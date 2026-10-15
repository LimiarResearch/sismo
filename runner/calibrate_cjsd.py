"""The default CJSD thresholds: the block statistics (D and I_x) on the development nulls of each base (null streams and shuffled
series), logged by python -m runner.run ... --calibrate-cjsd. The default threshold is the 1.0 quantile (the largest value observed:
zero warnings on the nulls); the grid uses the 0.9 and 0.99 quantiles.
python -m runner.calibrate_cjsd <development_run_folder>  -> protocol/cjsd_default.json"""
import glob, gzip, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
out = {}
for f in sorted(glob.glob(os.path.join(sys.argv[1], "*", "*_calibration", "*.json.gz"))):
    with gzip.open(f, "rt", encoding="utf-8") as g:
        o = json.load(g)
    b = o["series"]["base"]; d = out.setdefault(b, {"D": [], "Ix": [], "blocks": 0, "series": 0})
    d["series"] += 1
    for t, D, z, Ix in o["cjsd_log"]:
        d["blocks"] += 1; d["Ix"].append(Ix)
        if z > 3.0:
            d["D"].append(D)
for b, d in out.items():
    d["D"].sort(); d["Ix"].sort()
    print(f"{b:12s} series {d['series']:4d} blocks {d['blocks']:6d} | blocks with z > 3: {len(d['D'])} | max D {max(d['D']) if d['D'] else None} | max Ix {max(d['Ix']):.5f}")
json.dump(out, open(os.path.join(ROOT, "protocol", "cjsd_default.json"), "w"), indent=0)
