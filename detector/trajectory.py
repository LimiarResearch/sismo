"""The trajectories: what happens to each field after an input warning.
Each field keeps its NORMAL (mean and standard deviation), learned on the first BASE items of the stream (or on the BASE items before
the first episode, if that comes earlier). An episode opens when the detector warns of an input change in a field; later warnings on
the same field, while the episode is open, are updates of the same episode. Every STEP items: size = (mean of the last WIN items -
mean of the normal) / standard deviation of the normal; clarity = size * sqrt(WIN). State, from the mean of the last 3 sizes:
"growing" if the absolute size rose by more than 0.1 sd over 3 readings; "returning" if it fell by more than 0.1 sd; "stable"
otherwise; a new state only holds after 3 readings in a row. Events: opened, stopped_growing (with the peak), started_returning,
returned_to_normal (the displacement in the direction of the episode stays below 0.2 sd for 5 readings; crossing the normal to the
other side also counts as having returned), replaced (a new push in the same direction after stopping, by a warning or by sustained
growth that passes the previous peak by more than 0.4 sd; the old episode closes and a new one opens) and became_new_normal
(habituation: the floor of the episode, the smallest displacement in its direction over the readings of the last BASE items, stays
put, within 0.3 sd or within 0.3 of the floor itself, for H items; the plateau becomes the normal of the field)."""
import numpy as np

WIN, STEP, BASE = 300, 100, 1000
RETURN_LEVEL = 0.2           # the "returned to normal" level: below this for five readings, the episode closes


class Trajectories:
    def __init__(self, d, buf=8000, H=0, BASE=None, WIN=None, STEP=None):
        self.d = d; self.buf = np.zeros((buf, d)); self.nb = buf; self.t = -1; self.H = H
        self.BASE, self.WIN, self.STEP = BASE, WIN, STEP     # the declarable rulers; None = the module values
        self.open = {}; self.events = []; self.curves = []; self.normal = {}

    def _rulers(self):
        return (self.BASE or BASE), (self.WIN or WIN), (self.STEP or STEP)

    def _close(self, j):
        e = self.open.pop(j)
        self.curves.append({"field": j, "since": e["since"], "end": self.t, "curve": e["curve"], "peak": round(e["peak"], 2),
                            "warnings": e["warnings"], "base": e["base"]})

    def _base(self, j, since):
        if j not in self.normal:
            B, _, _ = self._rulers(); mb, sb = self._mean(since - B, since, j)
            if mb is None:
                return None
            self.normal[j] = (mb, sb)
        return self.normal[j]

    def _mean(self, a, b, j):
        a = max(a, self.t - self.nb + 1, 0); b = min(b, self.t + 1)
        if b - a < min(50, self._rulers()[1]):                      # minimum window of the mean: 50 items, or the declared WIN when smaller
            return None, None
        v = self.buf[np.arange(a, b) % self.nb, j]
        return float(v.mean()), float(v.std()) or 1e-9

    def _new_episode(self, j, since, base, warnings):
        return {"field": j, "since": since, "base": base, "curve": [], "state": "growing", "peak": 0.0, "t_peak": None, "low": 0,
                "warnings": warnings, "cand": None, "ncand": 0}

    def step(self, x, warnings=()):
        """x: the item; warnings: the records of the detector for this item (only phase 0 input warnings open episodes)."""
        self.t += 1; self.buf[self.t % self.nb] = x; B, J, P = self._rulers()
        if self.t == B - 1:
            for j in range(self.d):
                if j not in self.normal:
                    self.normal[j] = self._mean(0, B, j)
        for r in warnings:
            if r.get("phase") != 0 or r["kind"] != "VIRTUAL":
                continue
            for c in r["fields"]:
                j = int(c["index"])
                if j in self.open:
                    e0 = self.open[j]; dr = c.get("direction")
                    same = dr is not None and (dr == "up") == (e0["peak"] > 0)
                    if e0["state"] == "growing" or len(e0["curve"]) < 6 or not same:
                        self.open[j]["warnings"].append(r["t"]); continue
                    self.events.append({"field": j, "event": "replaced", "t": r["t"], "peak": round(self.open[j]["peak"], 2)})
                    self._close(j)
                base = self._base(j, r["since"])
                if base is None:
                    continue
                self.open[j] = self._new_episode(j, r["since"], base, [r["t"]])
                self.events.append({"field": j, "event": "opened", "t": r["t"], "since": r["since"]})
        if self.t % P == P - 1:
            for j, e in list(self.open.items()):
                m, _ = self._mean(self.t - J + 1, self.t + 1, j)
                size = (m - e["base"][0]) / e["base"][1]
                # The plateau is the floor of the episode: the smallest displacement, in its direction, over the readings of the last
                # BASE items. Oscillating above the floor (a cycle on top of a step, a slow growth) does not reset the clock; the floor
                # moving does, by more than 0.3 sd, or by more than 0.3 of the floor itself when it is above 1 sd.
                ext = size * (1.0 if (e["peak"] or size) > 0 else -1.0)
                e.setdefault("exts", []).append(ext); del e["exts"][:-max(1, B // P)]
                floor = min(e["exts"])
                if e.get("plateau_ref") is None or abs(floor - e["plateau_ref"]) > 0.3 * max(1.0, abs(e["plateau_ref"])):
                    e["plateau_ref"], e["plateau_since"] = floor, self.t
                dec = max(0.0, 1 - (self.t - e["plateau_since"]) / self.H) if self.H else 1.0
                e["curve"].append((self.t, round(size, 3), round(size * J ** 0.5, 1), e["state"], round(abs(size) * dec, 3)))
                if abs(size) > abs(e["peak"]):
                    e["peak"], e["t_peak"] = size, self.t
                if len(e["curve"]) >= 6:
                    now = np.mean([abs(v[1]) for v in e["curve"][-3:]]); before = np.mean([abs(v[1]) for v in e["curve"][-6:-3]])
                    raw = "growing" if now - before > 0.1 else ("returning" if before - now > 0.1 else "stable")
                    e["ncand"] = e["ncand"] + 1 if raw == e["cand"] else 1; e["cand"] = raw
                    new = raw if e["ncand"] >= 3 else e["state"]
                    if e["state"] == "growing" and new != "growing":
                        self.events.append({"field": j, "event": "stopped_growing", "t": self.t, "peak": round(e["peak"], 2)})
                    if e["state"] != "returning" and new == "returning":
                        self.events.append({"field": j, "event": "started_returning", "t": self.t})
                    if e["state"] != "growing" and new == "growing" and e.get("stopped") and abs(size) > abs(e["stopped"]) + 0.4:
                        self.events.append({"field": j, "event": "replaced", "t": self.t, "peak": round(e["peak"], 2)})
                        self._close(j); since = self.t - 2 * J
                        self.open[j] = self._new_episode(j, since, self.normal[j], [])
                        self.events.append({"field": j, "event": "opened", "t": self.t, "since": since, "without_warning": True})
                        continue
                    if new != "growing" and e["state"] == "growing":
                        e["stopped"] = e["peak"]
                    e["state"] = new
                # how far the field is still displaced in the direction of the episode: crossing the normal to the other side also
                # counts as having returned
                out = size * (1.0 if e["peak"] > 0 else -1.0) if e["peak"] else abs(size)
                e["low"] = e["low"] + P if out < RETURN_LEVEL else 0
                if e["low"] >= 5 * P and len(e["curve"]) >= 6:
                    self.events.append({"field": j, "event": "returned_to_normal", "t": self.t, "peak": round(e["peak"], 2)})
                    self._close(j); continue
                if self.H and self.t - e["plateau_since"] >= self.H:
                    mb, sb = self._mean(self.t - B + 1, self.t + 1, j)
                    self.events.append({"field": j, "event": "became_new_normal", "t": self.t, "peak": round(e["peak"], 2),
                                        "plateau": round(size, 2)})
                    self.normal[j] = (mb, sb); self._close(j)
