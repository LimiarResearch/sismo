"""The decision of the detector over the bins that fire at each item.
The first W items form the warm-up: the reference model (one logistic regression per class, one against the rest, with the
probabilities normalized) is trained on them. Then, at each item, the input axis and the relation axis step; if the mean of the input
e-values reaches log A, an input warning comes out (VIRTUAL, the log) with the accused bins; if the input is calm (mean below log A / 2)
and the relation mean reaches log A, a relation warning comes out (REAL, the alert) and the model is retrained on a new warm-up.
After an input warning, the input reference is rebuilt in every bin."""
import math

import numpy as np

from .evidence import InputAxis, RelationAxis, log_mean_exp, logistic_regression


def _probs(W, b):
    z = np.array([w[:-1] @ b + w[-1] for w in W])
    p = 1 / (1 + np.exp(-z))
    return p / p.sum()


class Decision:
    def __init__(self, n_bins, K=2, W=2000, A=200000.0, H=0, M=0):
        self.K = int(K)
        self.L, self.W, self.logA = n_bins, W, math.log(A)
        g = 1 - 1 / H if H else 1.0
        self.input = InputAxis(n_bins, g, M or 10 ** 12); self.relation = RelationAxis(max(2, self.K) * n_bins, g, M or 10 ** 12)
        self.buf = []; self.w = None

    def _train(self):
        Bm = np.array([u for u, _ in self.buf]); ym = np.array([v for _, v in self.buf])
        if self.K == 2:
            self.w = [logistic_regression(Bm, ym)]
        else:
            self.w = [logistic_regression(Bm, (ym == c).astype(float)) for c in range(self.K)]

    def _p(self, b):
        if self.K == 2:
            p = float(1 / (1 + np.exp(-(self.w[0][:-1] @ b + self.w[0][-1]))))
            return np.array([1 - p, p])
        return _probs(self.w, b)

    def _step_relation(self, idx, y, p):
        idx = np.asarray(idx)
        if self.K == 2:
            self.relation.step(idx, int(y == 1), p[1]); self.relation.step(idx + self.L, int(y == 0), p[0])
        else:
            for c in range(self.K):
                self.relation.step(idx + c * self.L, int(y == c), p[c])

    def _virtual(self):
        c = np.exp(self.input.lbf - self.input.lbf.max()); accused = np.flatnonzero(c >= .1 * c.sum())
        self.input.reset(np.arange(self.L)); self.relation.reset()
        return ("VIRTUAL", accused)

    def _real(self):
        lbf = self.relation.lbf; c = np.exp(lbf - lbf.max()); top = np.flatnonzero(c >= .1 * c.sum())
        top = top[np.argsort(-lbf[top])][:3]
        self.top_relation = [(int(i), float(self.relation.j[i]), float(self.relation.E[i])) for i in top]   # the most accused relation bins, for the record
        accused = np.unique(np.flatnonzero(c >= .1 * c.sum()) % self.L)
        self.w = None; self.buf = []; self.relation.reset()
        return ("REAL", accused)

    def update(self, idx, y):
        """idx: the bins that fire (one per field); y: the class. Returns None or (kind, accused bins)."""
        b = np.zeros(self.L); b[idx] = 1
        self.buf.append((b, int(y))); self.buf = self.buf[-self.W:]
        if self.w is None:
            if len(self.buf) >= self.W:
                self._train(); self.input.reset(); self.relation.reset()
            return None
        p = self._p(b)
        self.input.step(np.arange(self.L), b)
        self._step_relation(idx, int(y), p)
        mc = log_mean_exp(self.input.lbf)
        if mc >= self.logA:
            return self._virtual()
        if mc < self.logA / 2 and log_mean_exp(self.relation.lbf) >= self.logA:
            return self._real()
        return None
