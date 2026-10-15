"""KSWIN (river 0.26.1) with the same sampling and the same arithmetic, faster: the two-sample Kolmogorov-Smirnov test of stat_size
against stat_size items (method "auto", which is the exact one at these sizes) has a p-value determined only by the statistic D; the
p-value of each D is asked from scipy the first time and kept. The window, the sampling (random.Random(seed), restarted after each
alarm, as in river), the cut "p <= alpha and D > 0.1" and the restart are those of river. The equivalence with river is checked by
competitors/check_kswin.py."""
import collections
import itertools
import math
import random

import numpy as np
from scipy import stats

_P = {}


def _ks(a, b):
    """The statistic of scipy 1.17.1 ks_2samp, step by step, and the integer h that the exact method uses (d = h / lcm)."""
    a = np.sort(a); b = np.sort(b); n1, n2 = a.shape[0], b.shape[0]; both = np.concatenate([a, b])
    cd = np.searchsorted(a, both, side="right") / n1 - np.searchsorted(b, both, side="right") / n2
    minS = np.clip(-cd[np.argmin(cd)], 0, 1); maxS = cd[np.argmax(cd)]
    d = minS if minS > maxS else maxS
    g = math.gcd(n1, n2); lcm = (n1 // g) * n2; h = int(np.round(d * lcm))
    return h, h * 1.0 / lcm


class FastKSWIN:
    def __init__(self, alpha=0.005, window_size=100, stat_size=30, seed=None):
        self.alpha, self.window_size, self.stat_size, self.seed = alpha, window_size, stat_size, seed
        self._reset()

    def _reset(self):
        self.drift_detected = False; self.p_value = 0; self.n = 0
        self.window = collections.deque(maxlen=self.window_size); self._rng = random.Random(self.seed)

    def update(self, x):
        if self.drift_detected:
            self._reset()
        self.n += 1
        self.window.append(x)
        if len(self.window) >= self.window_size:
            rnd = [self.window[r] for r in self._rng.sample(range(self.window_size - self.stat_size), self.stat_size)]
            rec = list(itertools.islice(self.window, self.window_size - self.stat_size, self.window_size))
            h, st = _ks(np.asarray(rnd, float), np.asarray(rec, float))
            key = (self.stat_size, h)
            if key not in _P:
                st2, p = stats.ks_2samp(rnd, rec, method="auto")
                assert st2 == st, (st2, st)
                _P[key] = p
            self.p_value = _P[key]
            if self.p_value <= self.alpha and st > 0.1:
                self.drift_detected = True
                self.window = collections.deque(rec, maxlen=self.window_size)
            else:
                self.drift_detected = False
        else:
            self.drift_detected = False
