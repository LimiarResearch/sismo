"""The live record: every warning of the decision becomes a readable record, without changing the decision.
  destination  "alert" if the warning is REAL (the relation broke: retrain); "log" if it is VIRTUAL (the input changed; the model holds)
  since        estimated start of the change = item of the warning minus the stretch length of the most accused bin
  fields       for each accused field (its "index" and its name in "field"): mean before (up to 1,000 items before the start) and
               after (last up to 500 items), direction and size in standard deviations of the "before" (numeric fields); for
               categorical fields, the value whose share changed the most
  relation     (alerts) up to 3 of the most accused relation bins: class, field, value range of the bin, how many times the class
               appeared in that bin during the stretch (observed) and how many the reference model expected (expected)
  phases       the record comes out at the warning (phase 0) and is redone 200 and 500 items later (phases 200 and 500), with the
               "after" window already covering the change; an update carries "updates": the item of the original warning. The
               decision does not change.
Usage: det = Detector(X_warmup, numeric, K, names); for each item: records = det.step(x, y) -> list (empty, warning and/or updates)."""
import numpy as np

from .decision import Decision

W0, NB, BUF = 2000, 8, 6000


class Detector:
    def __init__(self, X0, numeric, K, names=None, W=None):
        X0 = np.asarray(X0); self.numeric = numeric; self.d = X0.shape[1]; self.W = W0 if W is None else int(W)
        self.names = names or [f"x{j}" for j in range(self.d)]
        self.cols = []
        for j in range(self.d):
            b = np.unique(np.quantile(X0[:, j], np.linspace(0, 1, NB + 1)[1:-1])) if numeric else np.unique(X0[:, j])[1:] - 0.5
            self.cols.append(b)
        self.start = np.cumsum([0] + [len(b) + 1 for b in self.cols])
        self.feat = np.concatenate([[j] * (len(b) + 1) for j, b in enumerate(self.cols)])
        self.L = int(self.start[-1]); self.K = K
        self.decision = Decision(self.L, K=K, W=self.W, H=0, M=0)
        self.buf = np.zeros((BUF, self.d)); self.t = 0; self.pending = []

    def indices(self, x):
        return np.array([self.start[j] + np.searchsorted(b, x[j], side="right") for j, b in enumerate(self.cols)])

    def _bin_range(self, j, k):
        b = self.cols[j]; lo = None if k == 0 else round(float(b[k - 1]), 4); hi = None if k == len(b) else round(float(b[k]), 4)
        return [lo, hi]

    def _window(self, a, b):
        a = max(a, self.t - BUF + 1, 0); b = min(b, self.t + 1)
        if b <= a:
            return None
        return self.buf[np.arange(a, b) % BUF]

    def _field(self, j, since):
        before = self._window(since - 1000, since); after = self._window(max(since, self.t - 499), self.t + 1)
        if before is None or after is None or len(before) < 50 or len(after) < 20:
            return {"field": self.names[j], "index": j}
        a, d = before[:, j], after[:, j]
        if self.numeric:
            sd = float(a.std()) or 1e-9; dif = float(d.mean() - a.mean())
            return {"field": self.names[j], "index": j, "direction": "up" if dif > 0 else "down", "before": round(float(a.mean()), 4),
                    "after": round(float(d.mean()), 4), "size_sd": round(dif / sd, 2)}
        vals = np.union1d(a, d); fa = np.array([np.mean(a == v) for v in vals]); fd = np.array([np.mean(d == v) for v in vals])
        k = int(np.argmax(np.abs(fd - fa)))
        return {"field": self.names[j], "index": j, "value": float(vals[k]), "share_before": round(float(fa[k]), 3),
                "share_after": round(float(fd[k]), 3)}

    def step(self, x, y):
        out = []
        r = self._step(x, y)
        if r is not None:
            r["phase"] = 0; out.append(r)
            self.pending.append((r["t"], r["since"] if r["since"] is not None else max(r["t"] - 300, 0), [c["index"] for c in r["fields"]], r))
        t = self.t - 1
        for (ta, since, fields, orig) in list(self.pending):
            for phase in (200, 500):
                if t == ta + phase:
                    up = {k: v for k, v in orig.items() if k not in ("fields", "phase")}
                    up.update({"phase": phase, "updates": ta, "t_update": t, "fields": [self._field(j, since) for j in fields]})
                    out.append(up)
            if t >= ta + 500:
                self.pending.remove((ta, since, fields, orig))
        return out

    def _step(self, x, y):
        self.buf[self.t % BUF] = x
        idx = self.indices(x)
        input_m = self.decision.input.m.copy(); input_lbf = self.decision.input.lbf.copy()
        r = self.decision.update(idx, int(y))
        t = self.t; self.t += 1
        if r is None:
            return None
        kind, accused = r[0], np.asarray(r[1])
        rec = {"t": t, "destination": "alert" if kind == "REAL" else "log", "kind": kind}
        if kind == "VIRTUAL":
            i = int(accused[np.argmax(input_lbf[accused])]) if len(accused) else int(np.argmax(input_lbf))
            since = int(t - input_m[i]); fields = sorted({int(self.feat[a]) for a in accused})
        else:
            since = None; fields = sorted({int(self.feat[a]) for a in accused})
        rec["since"] = since; rec["duration"] = (t - since) if since is not None else None
        rec["fields"] = [self._field(j, since if since is not None else max(t - 300, 0)) for j in fields]
        if kind == "REAL":
            rec["relation"] = []
            for i, obs, exp in self.decision.top_relation:
                b = i % self.L; block = i // self.L
                cls = (1 - block) if self.K == 2 else block
                j = int(self.feat[b]); k = int(b - self.start[j])
                rec["relation"].append({"class": int(cls), "field": self.names[j],
                                        "bin": self._bin_range(j, k) if self.numeric else float(k),
                                        "observed": round(obs, 1), "expected": round(exp, 1)})
        return rec
