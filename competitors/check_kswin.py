"""Checks that FastKSWIN gives the same alarms as the KSWIN of river 0.26.1, item by item, on random data (not on benchmark data).
python competitors/check_kswin.py"""
import os
import sys
import time

import numpy as np
from river import drift

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from competitors.kswin_fast import FastKSWIN  # noqa: E402

same = diff = 0; t_r = t_f = 0.0
for s in range(6):
    g = np.random.default_rng(1000 + s)
    x = np.concatenate([g.normal(size=4000), g.normal(0.7, 1, size=3000), g.integers(0, 3, size=3000).astype(float), g.normal(size=3000) * 3])
    for alpha, w, st in ((0.005, 100, 30), (1e-4, 300, 30), (1e-5, 300, 100), (0.005, 300, 30)):
        r = drift.KSWIN(alpha=alpha, window_size=w, stat_size=st, seed=1); f = FastKSWIN(alpha=alpha, window_size=w, stat_size=st, seed=1)
        a = []; b = []
        t0 = time.time()
        for i, v in enumerate(x):
            r.update(v)
            if r.drift_detected: a.append(i)
        t_r += time.time() - t0; t0 = time.time()
        for i, v in enumerate(x):
            f.update(v)
            if f.drift_detected: b.append(i)
        t_f += time.time() - t0
        if a == b: same += 1
        else: diff += 1; print("DIFFERENT", s, alpha, w, st, a[:5], b[:5])
print(f"fast KSWIN vs river: identical {same}/{same + diff}; time river {t_r:.1f} s, fast {t_f:.1f} s")
