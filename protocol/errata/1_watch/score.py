"""Erratum 1: the nulls of WATCH and CTM and the rows S1 and S2 recomputed on the outputs of sensitivity.py, with the rules of
metrics/rows.py (unchanged). Run from the root of the repository: python protocol/errata/1_watch/score.py <out folder>"""
import os
import sys

sys.path.insert(0, os.getcwd())
from metrics import rows as R


def main():
    outs = R.read(sys.argv[1]); print("series:", len(outs))
    nulls = [o for o in outs if o["series"]["name"] in R.NUL or o["series"]["variant"] == "shuffled"]
    for m in ("watch", "ctm"):
        for c in sorted({c for o in outs for c in o["methods"].get(m, {})}):
            ns = [o for o in nulls if c in o["methods"].get(m, {})]
            cells = []
            for kind in ("REAL", "VIRTUAL"):
                r = sum(any(a[1] == kind and a[0] >= o["series"]["score_start"] for a in o["methods"][m][c]) for o in ns)
                cells.append(f"{'alert' if kind == 'REAL' else 'log'} {r}/{len(ns)}")
            print(f"null {m}|{c}: {', '.join(cells)}")
    for L in R.synthetic(outs)[:2]:
        print(f"{L['row']}: detector {L['detector']:.3f}; best allowed {L['best_competitor']} {L['best_value']}; "
              f"se {L['se_difference']}; {L['verdict']}; {L['status']}")
        for key, v in L["per_method"].items():
            if key.startswith(("watch", "ctm")):
                print(f"    {key}: {v['f1']:.3f}")


if __name__ == "__main__":
    main()
