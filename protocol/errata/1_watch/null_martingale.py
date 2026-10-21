"""Erratum 1: the WATCH mixture martingale on independent uniform p-values (no change at all).
Runs the original composite_jumper_martingale (competitors/watch_original, unchanged) and a version where each jumper rate
redistributes its own wealth, and reports how often and how early the Shiryaev-Roberts statistic reaches 10^3 and 10^4 and the
martingale reaches 100. Run from the root of the repository: python protocol/errata/1_watch/null_martingale.py"""
import contextlib
import io
import os
import sys

import numpy as np

sys.path.insert(0, os.getcwd())
from competitors.methods import _sr
from competitors.watch_original import martingales as WM

N = 18000


def own_wealth(p):
    J = np.array([1e-4, 1e-3, 1e-2, 1e-1, 1.0]); A = np.full((5, 3), 1 / 3); out = []
    for x in p:
        A = (1 - J[:, None]) * A + (J[:, None] / 3) * A.sum(1, keepdims=True)
        A = A * np.array([1 - (x - 0.5), 1.0, 1 + (x - 0.5)]); out.append(A.sum(1).mean())
    return np.array(out)


def original(p):
    with contextlib.redirect_stdout(io.StringIO()):
        _, m, _, _ = WM.composite_jumper_martingale(p, return_alarm=True)
    return np.asarray(m, float)


def report(name, fn, reps):
    rng = np.random.default_rng(1); first = {1e3: [], 1e4: []}; ville = 0
    for _ in range(reps):
        m = fn(rng.uniform(size=N)); s = _sr(m); ville += m.max() >= 100
        for c in first:
            k = np.flatnonzero(s >= c)
            if len(k):
                first[c].append(int(k[0]))
    print(f"{name}: {reps} sequences of {N} uniform p-values; martingale >= 100 in {ville}")
    for c, L in first.items():
        print(f"  Shiryaev-Roberts >= {c:g}: {len(L)}/{reps}, median first item {np.median(L) if L else '-'}")


if __name__ == "__main__":
    report("original mixture", original, 40)
    report("each rate with its own wealth", own_wealth, 200)
