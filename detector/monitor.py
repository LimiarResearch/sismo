"""The monitor of a set of fields: the detector with the live record and the trajectories.
The first W0 items only go into the warm-up; at the W0-th item the detector is built from them, and the W0 items pass through it and
through the trajectories, in order. A field that starts flat (the warm-up does not show what it is: fewer than 3 distinct bin edges)
gets its bins from a ladder of representative values, declared from the minimum unit of the field (resolution); the ladder counts
units from where the field stood, with the edges halfway between units. The minimum unit is also the smallest standard deviation of
the normal in the trajectories. Neither enters as data: both are declarations of whoever connects the fields to the monitor."""
import numpy as np

from .reference import Detector
from .trajectory import Trajectories


def declared_scale(resolution, n=2000):
    """The scale of a field that starts flat: representative values from the declared minimum unit, on a ladder (0, 1, 2, 3, 5, 8,
    ... up to ten thousand units), denser at the bottom."""
    steps = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765, 10946]
    weights = np.array([6, 6, 5, 4, 4, 3, 3, 3, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1], float); weights = np.round(weights / weights.sum() * n).astype(int)
    cols = []
    for r in resolution:
        col = np.repeat(np.array(steps, float) * float(r), weights); cols.append(col[:n] if len(col) >= n else np.concatenate([col, np.full(n - len(col), col[-1])]))
    return np.stack(cols, axis=1)


class Monitor:
    def __init__(self, name, D, K=2, names=None, W0=2000, H=5000, scale=None, sd_min=None, W=None, BASE=None, WIN=None, STEP=None,
                 scale_only_if_flat=False, numeric=True):
        self.name, self.D, self.K, self.W0 = name, D, K, W0
        self.names = names or [f"{name}.x{j}" for j in range(D)]
        self.scale = None if scale is None else np.asarray(scale, float); self.sd_min = sd_min
        self.scale_only_if_flat = scale_only_if_flat
        self.W = W; self.numeric = numeric
        self.buf = []; self.det = None; self.tr = Trajectories(D, H=H, BASE=BASE, WIN=WIN, STEP=STEP); self.t = 0; self.n_events = 0

    def item(self, x, y=0):
        """Returns the records of this item (warnings, updates and trajectory events)."""
        if self.det is None:
            self.buf.append((np.asarray(x, float), y))
            if len(self.buf) < self.W0:
                return []
            X0 = np.array([b[0] for b in self.buf]) if self.scale is None else self.scale
            if self.scale is not None and self.scale_only_if_flat:
                X0 = np.array([b[0] for b in self.buf]); n = len(X0)
                for j in range(X0.shape[1]):
                    if len(np.unique(np.quantile(X0[:, j], np.linspace(0, 1, 9)[1:-1]))) < 3:      # one bin (or almost): the field has not shown what it is
                        col = self.scale[:, j]; units = np.diff(np.unique(col)); half = float(units[0]) / 2 if len(units) else 0.0
                        X0[:, j] = col[np.linspace(0, len(col) - 1, n).astype(int)] + (float(np.median(X0[:, j])) - half)
            self.det = Detector(X0, self.numeric, self.K, self.names, W=self.W)
            records = []
            for bx, by in self.buf:
                records += self._step(bx, by)
            self.buf = None
            return records
        return self._step(np.asarray(x, float), y)

    def _step(self, x, y):
        rs = self.det.step(x, y); self.tr.step(x, rs)
        if self.sd_min:
            for j, (m, sd) in list(self.tr.normal.items()):
                if sd < self.sd_min[j]:
                    self.tr.normal[j] = (m, self.sd_min[j])            # the declared minimum unit
        records = [dict(r, part=self.name) for r in rs]
        ev = self.tr.events[self.n_events:]; self.n_events = len(self.tr.events)
        records += [dict(e, kind="EVENT", part=self.name) for e in ev]
        self.t += 1
        return records
