"""The tuned configuration of each competitor, chosen in development (protocol, section 4.3):
- synthetic: the event F1 on the row that the kind of the method serves (alert: S1; log: S2; both kinds: the mean of S1 and S2);
- NAB, SMD, SMAP, MSL: the event F1 on the development series;
- company: the M1 sensitivity minus the M1 rate on the no-defect null.
Ties: fewer false warnings per 1,000 items; then the configuration key. The detector has no tuned configuration.
python -m runner.tune <development_run_folder> [--lives DIR]  -> protocol/tuned.json and <run>/tuning_objectives.json"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from runner import configs as C  # noqa: E402
from metrics import rows as R  # noqa: E402


def config_of(method, key):
    mb = C.base_method(method)
    for c in [C.DEFAULT[mb]] + C.GRID.get(mb, []):
        k = C.config_key({kk: vv for kk, vv in c.items()})
        if k == key or (mb == "cjsd" and all(f"{kk}={vv}" in key for kk, vv in c.items())):
            return c
    raise KeyError((method, key))


def choose(values, false):
    """values: {"method|cfg": objective}; returns {method: cfg} with the largest objective, then the fewest false warnings."""
    by = {}
    for k, v in values.items():
        if v is None:
            continue
        m, c = k.split("|", 1)
        if m == "detector":
            continue
        by.setdefault(m, []).append((-v, false.get(k, 0.0), c))
    return {m: sorted(l)[0][2] for m, l in by.items()}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("--lives", default=None); a = ap.parse_args()
    outputs = R.read(a.run); out = {}; report = {}
    synth = [o for o in outputs if o["series"]["base"] == "synthetic"]
    if synth:
        ls = {L["row"][:2]: L for L in R.synthetic(synth) if "per_method" in L and isinstance(L["per_method"], dict) and L["row"][:2] in ("S1", "S2")}
        val = {}; fal = {}
        for k in ls["S1"]["per_method"]:
            m = k.split("|")[0]; kinds = R.method_kinds(m)
            f1 = [ls[s]["per_method"][k]["f1"] for s, tp in (("S1", "REAL"), ("S2", "VIRTUAL")) if tp in kinds]
            val[k] = sum(f1) / len(f1); fal[k] = ls["S2"]["per_method"][k]["false_per_1000"] or 0.0
        out["synthetic"] = {m: config_of(m, c) for m, c in choose(val, fal).items()}; report["synthetic"] = val
    for base in ("nab", "smd", "smap", "msl"):
        if any(o["series"]["base"] == base for o in outputs):
            L = R.public(outputs, base)[0]
            val = {k: v["f1"] for k, v in L["per_method"].items()}; fal = {k: v["false_per_1000"] or 0.0 for k, v in L["per_method"].items()}
            out[base] = {m: config_of(m, c) for m, c in choose(val, fal).items()}; report[base] = val
    if a.lives and any(o["series"]["base"] == "company" for o in outputs):
        L = next(L for L in R.company(outputs, a.lives) if L["row"].startswith("M1"))
        val = {k: v["sensitivity"] - L["info"]["null"][k] for k, v in L["per_method"].items() if v["sensitivity"] is not None}
        out["company"] = {m: config_of(m, c) for m, c in choose(val, {}).items()}; report["company"] = val
    json.dump(out, open(os.path.join(ROOT, "protocol", "tuned.json"), "w"), indent=1, ensure_ascii=False)
    json.dump(report, open(os.path.join(a.run, "tuning_objectives.json"), "w"), indent=1, ensure_ascii=False)
    for b, d in out.items():
        print(b, json.dumps(d, ensure_ascii=False))


if __name__ == "__main__":
    main()
