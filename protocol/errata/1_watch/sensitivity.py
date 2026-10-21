"""Erratum 1, sensitivity (information only, outside the verdict): WATCH and CTM on the approval synthetic series with the martingale
threshold alone (Ville 100, no Shiryaev-Roberts) and with the strictest point of the protocol grid (Ville 1,000, Shiryaev-Roberts 10^6).
Each published output is copied with the two extra configurations added to "watch" and "ctm"; nothing else changes.
Run from the root of the repository:
  python protocol/errata/1_watch/sensitivity.py <publication outputs>/synthetic/main <out folder> [process] [of]
It skips the series already written, so it can be resumed and split across processes."""
import gzip
import glob
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from competitors import methods as M
from runner import run as RR

CONFIGS = {"sr=inf,ville=100.0": {"ville": 100.0, "sr": float("inf")},
           "sr=1000000.0,ville=1000.0": {"ville": 1000.0, "sr": 1e6}}


def main():
    pub, out = sys.argv[1], sys.argv[2]
    k, n = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, 1)
    os.makedirs(out, exist_ok=True)
    published = {}
    for f in glob.glob(os.path.join(pub, "*.json.gz")):
        s = json.load(gzip.open(f))["series"]; published[(s["name"], s["variant"], s["seed"])] = f
    for i, s in enumerate(RR.load("synthetic", "approval", "main", None, None)):
        if i % n != k:
            continue
        f = published[(s.name, s.variant, s.seed)]; dst = os.path.join(out, os.path.basename(f))
        if os.path.exists(dst):
            continue
        o = json.load(gzip.open(f)); cache = {}
        for m in ("watch", "ctm"):
            if m == "ctm" and s.y is None:
                continue
            for key, cfg in CONFIGS.items():
                o["methods"][m][key] = M.watch(s, cfg, weighted=(m == "watch"), cache=cache)
        with gzip.open(dst + ".tmp", "wt", encoding="utf-8") as g:
            json.dump(o, g)
        os.replace(dst + ".tmp", dst); print(i, s.name, s.variant, flush=True)


if __name__ == "__main__":
    main()
