"""The NAB's own score (standard profile), computed with NAB's own code (commit ea702d7, downloaded by data/download.py) without
change, in a separate environment (pandas 1.5.3, numpy 1.26.4; see protocol/ENVIRONMENT.txt). Each method becomes a "detector" in the
NAB results format: score 1 at the item of each warning and 0 elsewhere, threshold 0.5. The corpus is a copy restricted to the
requested series, with their windows.

python -m metrics.nab_score <official_outputs_folder> <nab_python> <raw_data_dir> <work_dir> [--json nab.json] [--part approval|development]
  official_outputs_folder: the outputs of the NAB "official" variant (<outputs>/<run>/nab/official)"""
import argparse
import csv
import glob
import gzip
import json
import os
import shutil
import subprocess



def detector_name(method, cfg):
    """NAB cuts the detector name at the first "_": the name is "m" and 10 hex digits of the sha256 of "method|configuration", written
    with the names of the approval run (runner/legacy.py): NAB sums the per-file scores in the order of its directory listing, which
    depends on the result file names, and the last digits of the scores depend on that order."""
    import hashlib
    from runner import legacy
    return "m" + hashlib.sha256(legacy.method_config(method, cfg).encode()).hexdigest()[:10]


def is_default(method, cfg):
    """The default configuration of the method (runner/configs.py, DEFAULT); for CJSD, the default quantiles (the thresholds come from
    the calibration)."""
    from runner import configs as C
    p = C.DEFAULT[C.base_method(method)]
    parts = dict(x.split("=", 1) for x in cfg.split(",")) if cfg != "default" else {}
    return all(parts.get(k) == str(v) for k, v in p.items())


def build(outputs, raw, work, configs):
    nab_root = os.path.join(raw, "nab"); code = os.path.join(raw, "nab_code")
    if os.path.exists(work):
        shutil.rmtree(work)
    shutil.copytree(code, work)
    os.makedirs(os.path.join(work, "labels")); os.makedirs(os.path.join(work, "results"))
    windows = json.load(open(os.path.join(nab_root, "labels/combined_windows.json")))
    names = sorted({o["series"]["name"] for o in outputs})
    json.dump({k: windows[k] for k in names}, open(os.path.join(work, "labels/combined_windows.json"), "w"))
    for k in names:
        os.makedirs(os.path.join(work, "data", os.path.dirname(k)), exist_ok=True)
        shutil.copy(os.path.join(nab_root, "data", k), os.path.join(work, "data", k))
    thresholds = {}; detectors = {}
    for o in outputs:
        k = o["series"]["name"]; rows = list(csv.reader(open(os.path.join(nab_root, "data", k))))[1:]
        for method, cs in o["methods"].items():
            for cfg, warnings in cs.items():
                if configs == "default" and not is_default(method, cfg):
                    continue
                det = detector_name(method, cfg); detectors[det] = (method, cfg)
                thresholds[det] = {p: {"threshold": 0.5, "score": 0.0} for p in ("standard", "reward_low_FP_rate", "reward_low_FN_rate")}
                d = os.path.join(work, "results", det, os.path.dirname(k)); os.makedirs(d, exist_ok=True)
                marked = {a[0] for a in warnings}
                with open(os.path.join(d, f"{det}_{os.path.basename(k)}"), "w", newline="") as f:
                    w = csv.writer(f); w.writerow(["timestamp", "value", "anomaly_score"])
                    for i, (ts, v) in enumerate(rows):
                        w.writerow([ts, v, 1.0 if i in marked else 0.0])
    thresholds["null"] = {p: {"threshold": 0.5, "score": 0.0} for p in ("standard", "reward_low_FP_rate", "reward_low_FN_rate")}
    for k in names:                                   # the NAB null detector: score 0 everywhere (the base of the normalization)
        rows = list(csv.reader(open(os.path.join(nab_root, "data", k))))[1:]
        d = os.path.join(work, "results", "null", os.path.dirname(k)); os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"null_{os.path.basename(k)}"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["timestamp", "value", "anomaly_score"])
            for ts, v in rows:
                w.writerow([ts, v, 0.0])
    json.dump(thresholds, open(os.path.join(work, "config/thresholds.json"), "w"))
    return detectors


def score(work, python, detectors):
    subprocess.run([python, "run.py", "-d", ",".join(detectors + ["null"]), "--score", "--normalize", "--skipConfirmation"],
                   cwd=work, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return json.load(open(os.path.join(work, "results/final_results.json")))


def main():
    ap = argparse.ArgumentParser(description="The NAB score of every method, with the NAB code.")
    ap.add_argument("outputs"); ap.add_argument("python"); ap.add_argument("raw"); ap.add_argument("work")
    ap.add_argument("--json", default=None); ap.add_argument("--part", default="approval")
    a = ap.parse_args()
    if os.sep in a.python:                            # NAB runs from inside the work folder: a relative path would not resolve
        a.python = os.path.abspath(a.python)
    outputs = []
    for f in sorted(glob.glob(os.path.join(a.outputs, "*.json.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as g:
            o = json.load(g)
        if o["series"]["variant"] == "official":
            outputs.append(o)
    out = {}
    # 1) the series of the part, every configuration; 2) if the run has the 58 series, the 58 with the default configurations
    groups = [("part_series", [o for o in outputs if o["series"]["part"] == a.part], "all")]
    if len({o["series"]["name"] for o in outputs}) == 58:
        groups.append(("all_58_default", outputs, "default"))
    for label, ss, cf in groups:
        work = os.path.join(a.work, label)
        dets = build(ss, a.raw, work, cf)
        res = score(work, a.python, sorted(dets))
        out[label] = {"series": len(ss), "scores": {f"{dets[d][0]}|{dets[d][1]}": res[d]["standard"] for d in dets if d in res}}
        print(f"{label} ({len(ss)} series)")
        for d, v in sorted(out[label]["scores"].items(), key=lambda kv: -kv[1]):
            print(f"  {d:70s} {v:8.2f}")
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
