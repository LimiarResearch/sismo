"""The runner of the benchmark: runs every method on one base and writes one output per series, resuming where it stopped.

python -m runner.run <run> <base> <part> [--variant V] [--configs default|grid|approval] [--process k --of P]
                     [--outputs DIR] [--raw DIR] [--lives DIR] [--calibrate-cjsd] [--only KEY ...]
  base: synthetic | nab | smd | smap | msl | company;  part: development | approval
  --variant           main (default) | official | warmup500 (NAB only)
  --configs default   only the default configuration of each method
            grid      the default and the whole grid (development)
            approval  the default and the tuned one (protocol/tuned.json)
  --calibrate-cjsd    only the log of the CJSD block statistics on the null series (for the default thresholds)
  --only KEY          only the series whose "name", "name|seed" or "variant|name|seed" is KEY (repeatable)
  --raw               the public data downloaded by data/download.py (default data/raw)
  --lives             the folder with the lives of the company (base company)
Process k of P runs the series of index i with i % P == k (separate processes split the series). A series whose output is already
written does not run again (resume); the resume log is <outputs>/<run>/resume.txt."""
import argparse
import gzip
import hashlib
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from competitors import methods as M  # noqa: E402
from runner import configs as C  # noqa: E402
from runner import legacy  # noqa: E402
from runner import series as S  # noqa: E402

DEV_SYNTH = list(range(20000, 20010))
NOT_RUN_HTM = "cost (about 6.6 s per 1,000 points per field; see HTM_FIELDS in runner/configs.py)"


def protocol(filename):
    p = os.path.join(ROOT, "protocol", filename)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def seed_of(name):
    return int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)


def shuffled_public(lst, everything):
    """The shuffled series of a public base: all of them on NAB; on SMD, SMAP and MSL, the third chosen by the hash of the name
    (int(sha256(name)[8:16], 16) % 3 == 0), because of the cost; their main null is the training stretch."""
    out = []
    for s in lst:
        if s.variant != "main":
            continue
        if everything or int(hashlib.sha256(s.name.encode()).hexdigest()[8:16], 16) % 3 == 0:
            out.append(S.shuffle(s, seed_of("embaralhar|" + s.name)))
    return out


def load(base, part, variant, raw, lives):
    if base == "synthetic":
        seeds = DEV_SYNTH if part == "development" else protocol("seeds.json")["synthetic"]
        lst = S.synthetic(seeds, part, shuffled=False)
        changing = [s for s in lst if s.extra["expected"] is not None]
        shuffled_seeds = set(seeds[:10] if part == "approval" else seeds[:3])   # shuffled: 10 seeds per stream with a change (3 in development)
        return lst + [S.shuffle(s, 7_000_000 + s.seed) for s in changing if s.seed in shuffled_seeds]
    if base == "nab":
        # official in the approval run: the 58 series (the NAB score on the 58 uses only the default configurations; protocol, section 6, P1o)
        lst = [s for s in S.nab(raw, variant) if s.part == part or (variant == "official" and part == "approval")]
        return lst + (shuffled_public(lst, True) if variant == "main" else [])
    if base in ("smd", "smap", "msl"):
        lst = S.smd(raw) if base == "smd" else S.smap_msl(raw, base.upper())
        lst = [s for s in lst if s.part == part]
        return lst + shuffled_public(lst, part == "development")
    if base == "company":
        from runner import company as E
        out = []
        for life in sorted(os.listdir(lives)):
            if os.path.exists(os.path.join(lives, life, "verdade.json")):
                out += E.series(os.path.join(lives, life), part, life)
        if part == "development":                  # to calibrate CJSD: the processes of the normal life with the minutes in random order
            out += [S.shuffle(s, seed_of("embaralhar|" + s.name)) for s in out if s.extra["life"].startswith("normal")]
        return out
    raise KeyError(base)


def configs_for(method, mode, base, cal):
    mb = C.base_method(method)
    if mode == "default":
        cs = [C.DEFAULT[mb]]
    elif mode == "grid":
        cs = [C.DEFAULT[mb]] + [c for c in C.GRID.get(mb, []) if c != C.DEFAULT[mb]]
    else:
        tuned = protocol("tuned.json").get(base, {}).get(method)
        cs = [C.DEFAULT[mb]] + ([tuned] if tuned and tuned != C.DEFAULT[mb] else [])
    if mb == "cjsd":
        out = []
        for c in cs:
            q = cal.get(base)
            if not q:
                continue
            c = dict(c, tau=float(np.quantile(q["D"], c["q_tau"])) if q.get("D") else None, tau_x=float(np.quantile(q["Ix"], c["q_tau_x"])))
            out.append(c)
        return out
    return cs


def output_file_name(s):
    """The output file of a series: the first 20 hex digits of the sha256 of "base|name|variant|seed", written with the names of the
    approval run (runner/legacy.py), so a run of this code writes the same file names as that run. The metrics read the outputs in
    file-name order, and the company rows resample the lives in the order in which they first appear (metrics/rows.py)."""
    key = legacy.series_key(s.base, s.name, s.variant, s.seed)
    return hashlib.sha256(key.encode()).hexdigest()[:20] + ".json.gz"


def meta(s):
    return {"base": s.base, "name": s.name, "part": s.part, "variant": s.variant, "seed": s.seed, "n": s.n, "d": s.d,
            "warmup": s.warmup, "score_start": s.score_start, "out_of_reach": s.out_of_reach,
            "minutes_per_item": s.minutes_per_item, "ignore": s.ignore, "field_names": s.field_names,
            "events": [{"start": e.start, "end": e.end, "window": list(e.window), "fields": None if e.fields is None else sorted(e.fields),
                        "kind": e.kind, "mark": e.mark, "extra": e.extra} for e in s.events],
            "extra": {k: v for k, v in s.extra.items() if k not in ("timestamps",)}}


def in_grid(s):
    """In development, the grid runs only on the series that the choice of the tuned configuration looks at; the others run only the
    default configuration."""
    if s.variant != "main":
        return False
    if s.base == "synthetic":
        return s.extra.get("expected") is not None and s.name not in ("slow_real", "cat_real", "xor")
    if s.base == "company":
        return s.extra["life"].startswith(("normal", "sem_defeito"))
    return True


def run_series(s, mode, base, cal, calibrate=False):
    if mode == "grid" and not in_grid(s):
        mode = "default"
    out = {"series": meta(s), "methods": {}, "detector": None, "seconds": {}, "not_run": {}}
    cache = {}
    if calibrate:
        log = []; t0 = time.time(); M.cjsd(s, {}, cache, log=log)
        out["cjsd_log"] = log; out["seconds"]["cjsd"] = time.time() - t0
        return out
    for method in M.methods_for_series(s):
        mb = C.base_method(method)
        if mb == "htm" and base not in C.HTM_FIELDS:
            out["not_run"][method] = NOT_RUN_HTM; continue
        t0 = time.time()
        if method == "detector":
            w, rep, ev = M.run("detector", s, {"own_warmup": s.variant == "warmup500"})
            out["detector"] = {"warnings": w, "reports": rep, "events": ev}
            out["methods"]["detector"] = {C.config_key(C.DEFAULT["detector"]): w}
        else:
            res = {}
            for cfg in configs_for(method, mode, base, cal):
                res[C.config_key(cfg)] = M.run(method, s, cfg, cache, htm_fields=C.HTM_FIELDS.get(base))
            out["methods"][method] = res
        out["seconds"][method] = time.time() - t0
    return out


def main():
    ap = argparse.ArgumentParser(description="Runs every method on one base and writes one output per series.")
    ap.add_argument("run"); ap.add_argument("base"); ap.add_argument("part")
    ap.add_argument("--variant", default="main"); ap.add_argument("--configs", default="default", choices=("default", "grid", "approval"))
    ap.add_argument("--process", type=int, default=0); ap.add_argument("--of", type=int, default=1)
    ap.add_argument("--outputs", default=os.path.join(ROOT, "outputs")); ap.add_argument("--raw", default=os.path.join(ROOT, "data", "raw"))
    ap.add_argument("--lives", default=None); ap.add_argument("--calibrate-cjsd", action="store_true")
    ap.add_argument("--only", action="append", default=None)
    a = ap.parse_args()
    import warnings
    warnings.filterwarnings("ignore")
    lst = load(a.base, a.part, a.variant, a.raw, a.lives)
    if a.calibrate_cjsd:
        lst = [s for s in lst if s.variant == "shuffled" or (s.base == "synthetic" and (s.name.startswith("null") or s.name == "slow_null"))]
    if a.only:
        lst = [s for s in lst if {s.name, f"{s.name}|{s.seed}", f"{s.variant}|{s.name}|{s.seed}"} & set(a.only)]
    folder = os.path.join(a.outputs, a.run, a.base, a.variant + ("_calibration" if a.calibrate_cjsd else "")); os.makedirs(folder, exist_ok=True)
    cal = protocol("cjsd_default.json")
    log = open(os.path.join(a.outputs, a.run, "resume.txt"), "a")
    for i, s in enumerate(lst):
        if i % a.of != a.process:
            continue
        path = os.path.join(folder, output_file_name(s))
        if os.path.exists(path):
            continue
        t0 = time.time()
        out = run_series(s, a.configs, a.base, cal, a.calibrate_cjsd)
        with gzip.open(path + ".partial", "wt", encoding="utf-8") as f:
            json.dump(out, f)
        os.replace(path + ".partial", path)
        log.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} done {a.base} {a.variant} {s.name} {s.seed} {time.time() - t0:.1f}s\n"); log.flush()


if __name__ == "__main__":
    main()
