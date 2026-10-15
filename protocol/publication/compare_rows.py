"""Compares the rows (metrics/rows.py) and the NAB score (metrics/nab_score.py) of the approval run, written with the names of that run,
with those computed by this code, after translating the original ones with protocol/publication/keymap.json. Every value is compared
exactly (numbers, lists, verdicts and statuses); the labels of the rows are matched through the keymap. Rows that exist only in the new
results are listed apart (they are not an error).

python protocol/publication/compare_rows.py <original_rows.json> <new_rows.json> [--nab <original_nab.json> <new_nab.json>]
Exits with status 1 on any difference or on an original row without a new one."""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KM = json.load(open(os.path.join(HERE, "keymap.json"), encoding="utf-8"))
RK, RV = KM["rows"]["keys"], KM["rows"]["values"]
TYPES = KM["synthetic_type"]


def method_cfg(k):
    """"method|cfg" of the approval run in the current form."""
    if "|" not in k:
        return k
    m, c = k.split("|", 1)
    if m not in KM["method"]:
        return k
    if c in KM["config_label"]:
        c2 = KM["config_label"][c]
    else:
        names = KM["config_parameter"].get(m.split("/")[0], {})
        c2 = ",".join(f"{a}={b}" for a, b in sorted((names.get(a, a), b) for a, b in (p.split("=", 1) for p in c.split(","))))
    return f"{KM['method'][m]}|{c2}"


def text(s):
    if s in RV:
        return RV[s]
    for a, b in KM["rows"]["info_text"].items():
        s = s.replace(a, b)
    return s


def translate(x):
    if isinstance(x, dict):
        return {TYPES.get(k, RK.get(k, method_cfg(k))): translate(v) for k, v in x.items()}
    if isinstance(x, list):
        return [translate(v) for v in x]
    if isinstance(x, str):
        return method_cfg(text(x))
    return x


def numbers(s):
    return re.findall(r"-?\d+(?:[.,]\d+)?", s)


def diff(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in b:
                out.append(f"{path}/{k}: only in the original")
            elif k not in a:
                out.append(f"{path}/{k}: only in the new")
            else:
                diff(a[k], b[k], f"{path}/{k}", out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f"{path}[{i}]", out)
    elif isinstance(a, str) and isinstance(b, str) and a != b:
        # free text of the info: the numbers in it must be the same
        if numbers(a) != numbers(b) or not numbers(a):
            out.append(f"{path}: {a!r} != {b!r}")
    elif a != b and not (isinstance(a, str) and isinstance(b, str)):
        out.append(f"{path}: {a!r} != {b!r}")


def compare_rows(orig, new):
    labels = KM["rows"]["labels"]
    new_by = {L["row"]: L for L in new}
    errors = 0; seen = set()
    for L in orig:
        old_label = L["linha"]; label = labels.get(old_label, old_label)
        if label not in new_by:
            print(f"  MISSING IN NEW: {old_label}"); errors += 1; continue
        seen.add(label)
        t = translate({k: v for k, v in L.items() if k != "linha"})
        n = {k: v for k, v in new_by[label].items() if k != "row"}
        out = []
        diff(t, n, "", out)
        extra = [x for x in out if x.endswith("only in the new")]
        real = [x for x in out if not x.endswith("only in the new")]
        if real:
            errors += 1
            print(f"  DIFFERENT {label}: " + "; ".join(real[:8]))
        else:
            print(f"  identical {label}" + (f" (new keys: {', '.join(x.split(':')[0] for x in extra)})" if extra else ""))
    for label in new_by:
        if label not in seen:
            print(f"  only in the new results: {label}")
    return errors


def compare_nab(orig, new):
    errors = 0
    for group, v in orig.items():
        g = KM["nab_score_keys"].get(group, group)
        if g not in new:
            print(f"  MISSING IN NEW: {g}"); errors += 1; continue
        t = {method_cfg(k): x for k, x in v["pontuacao"].items()}
        n = new[g]["scores"]
        bad = [k for k in sorted(set(t) | set(n)) if t.get(k) != n.get(k)]
        if v["series"] != new[g]["series"] or bad:
            errors += 1; print(f"  DIFFERENT {g}: series {v['series']} vs {new[g]['series']}; " + "; ".join(f"{k}: {t.get(k)} != {n.get(k)}" for k in bad[:8]))
        else:
            print(f"  identical {g}: {len(t)} scores, {v['series']} series")
    return errors


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("original"); ap.add_argument("new"); ap.add_argument("--nab", nargs=2, default=None)
    a = ap.parse_args()
    e = compare_rows(json.load(open(a.original, encoding="utf-8")), json.load(open(a.new, encoding="utf-8")))
    if a.nab:
        e += compare_nab(json.load(open(a.nab[0], encoding="utf-8")), json.load(open(a.nab[1], encoding="utf-8")))
    print("rows: " + ("all identical" if not e else f"{e} differences"))
    return 1 if e else 0


if __name__ == "__main__":
    sys.exit(main())
