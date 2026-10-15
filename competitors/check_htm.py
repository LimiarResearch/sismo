"""Checks the HTM port (competitors/htm_nab.py) against the published score of the htmcore detector of the NAB community
(htm-community/NAB, commit 98cdba6, results/final_results.json: standard profile 63.08 on the whole corpus; the repository does not
keep the result files). Runs the port on the 58 NAB series with the real timestamps and seed 1, writes the raw scores as NAB writes
them, scores them with NAB's own code (the htmcore threshold of the community config/thresholds.json, 0.5014 in the standard profile)
and, for comparison, also scores the same scores turned into warnings as in the benchmark (threshold, after the probationary period,
warnings merged when less than 10 items apart). Uses neither the shuffled series nor anything of the benchmark besides the port and
the converter.
python competitors/check_htm.py <raw_data_dir> <nab_python> <work_dir> [processes]"""
import csv
import json
import math
import os
import shutil
import subprocess
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from competitors.methods import merge  # noqa: E402

THRESHOLD = {"standard": 0.5014187204194446, "reward_low_FP_rate": 0.5122987896930875, "reward_low_FN_rate": 0.5014187204194446}
PUBLISHED = 63.081419488725054


def scores_of(args):
    from competitors.htm_nab import scores
    raw, name, dest = args
    if os.path.exists(dest):
        return name
    rows = list(csv.reader(open(os.path.join(raw, "nab", "data", name))))[1:]
    s = scores([float(v) for _, v in rows], [ts for ts, _ in rows], {"seed": 1})
    np.save(dest + ".partial.npy", np.asarray(s, float)); os.replace(dest + ".partial.npy", dest)
    return name


def main():
    raw, py_nab, work = sys.argv[1:4]; proc = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    windows = json.load(open(os.path.join(raw, "nab", "labels", "combined_windows.json")))
    names = sorted(windows); cache = os.path.join(work, "scores"); os.makedirs(cache, exist_ok=True)
    path = {k: os.path.join(cache, k.replace("/", "__") + ".npy") for k in names}
    with Pool(proc) as p:
        for k in p.imap_unordered(scores_of, [(raw, k, path[k]) for k in names]):
            print("scores", k, flush=True)
    nab = os.path.join(work, "nab")
    if os.path.exists(nab):
        shutil.rmtree(nab)
    shutil.copytree(os.path.join(raw, "nab_code"), nab)
    os.makedirs(os.path.join(nab, "labels")); shutil.copy(os.path.join(raw, "nab", "labels", "combined_windows.json"), os.path.join(nab, "labels"))
    shutil.copytree(os.path.join(raw, "nab", "data"), os.path.join(nab, "data"))
    for k in names:
        rows = list(csv.reader(open(os.path.join(raw, "nab", "data", k))))[1:]; s = np.load(path[k]); n = len(rows)
        prob = int(min(math.floor(0.15 * n), 0.15 * 5000))
        warned = {a[0] for a in merge([(int(t), 0, None) for t in np.flatnonzero(s[prob:] >= THRESHOLD["standard"]) + prob])}
        for det, col in (("htmcore", s), ("htmwarnings", np.array([1.0 if i in warned else 0.0 for i in range(n)])), ("null", np.zeros(n))):
            d = os.path.join(nab, "results", det, os.path.dirname(k)); os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, f"{det}_{os.path.basename(k)}"), "w", newline="") as f:
                w = csv.writer(f); w.writerow(["timestamp", "value", "anomaly_score"])
                for (ts, v), x in zip(rows, col):
                    w.writerow([ts, v, float(x)])
    lim = {"htmcore": {p: {"threshold": c, "score": 0.0} for p, c in THRESHOLD.items()},
           "htmwarnings": {p: {"threshold": 0.5, "score": 0.0} for p in THRESHOLD}, "null": {p: {"threshold": 0.5, "score": 0.0} for p in THRESHOLD}}
    json.dump(lim, open(os.path.join(nab, "config", "thresholds.json"), "w"))
    subprocess.run([py_nab, "run.py", "-d", "htmcore,htmwarnings,null", "--score", "--normalize", "--skipConfirmation"], cwd=nab, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    r = json.load(open(os.path.join(nab, "results", "final_results.json")))
    print(f"port, raw scores (as NAB): {r['htmcore']['standard']:.2f}  (published: {PUBLISHED:.2f})")
    print(f"port, turned into warnings as in the benchmark: {r['htmwarnings']['standard']:.2f}")


if __name__ == "__main__":
    main()
