"""The hash of each series of a run: the sha256 of the sorted JSON with the warning lists of every method and configuration and with
the phase 500 reports and the trajectory events of the detector (without the machine time). One line per series, sorted by the key
"base|variant|name|seed" (with "|calibration" for the CJSD calibration logs).
python -m runner.warnings_manifest <run_folder>"""
import glob, gzip, hashlib, json, os, sys
lines = []
for f in glob.glob(os.path.join(sys.argv[1], "**", "*.json.gz"), recursive=True):
    with gzip.open(f, "rt", encoding="utf-8") as g:
        o = json.load(g)
    m = o["series"]; key = f"{m['base']}|{m['variant']}|{m['name']}|{m['seed']}" + ("|calibration" if "cjsd_log" in o else "")
    body = {"methods": o["methods"], "detector": o["detector"], "cjsd_log": o.get("cjsd_log")}
    lines.append(f"{hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}  {key}")
print("\n".join(sorted(lines, key=lambda l: l[66:])))
