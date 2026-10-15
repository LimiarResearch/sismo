"""Compares the outputs of the approval run (written with the names of that run) with the outputs of a run of this code, series by
series, after translating the original outputs with protocol/publication/keymap.json. Also converts the original outputs to the
current schema, so that the metrics can be computed on them without running the methods again.

python protocol/publication/compare_runs.py <original_run_folder> <new_run_folder> [--sample] [--show N]
  compares every original series output with the new output of the same series ("base|variant|name|seed"): the series description,
  the warning lists of every method and configuration, the detector outputs (warnings, phase 500 reports, trajectory events), the
  methods not run and the CJSD calibration log; the machine time is not compared. Prints the series compared, identical, different
  and missing on either side, and exits with status 1 on any difference or missing series.
  --sample   only the series present in the new run are expected (originals without a new output are not counted as missing)
  --show N   details of at most N differing series (default 20)

python protocol/publication/compare_runs.py --convert <original_run_folder> <output_folder>
  writes the translated original outputs as <output_folder>/<base>/<variant folder>/<file>.json.gz, with the file names that the
  runner writes (runner.run.output_file_name), and links <output_folder>/lives to the lives of the original run."""
import argparse
import glob
import gzip
import json
import os
import sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
KM = json.load(open(os.path.join(HERE, "keymap.json"), encoding="utf-8"))
K = KM["output_keys"]


def method(m):
    return KM["method"][m]


def config(m, cfg):
    """An original configuration key ("alfa=0.01,janela=500,passo=50") renamed and rendered in the current sorted form."""
    if cfg in KM["config_label"]:
        return KM["config_label"][cfg]
    names = KM["config_parameter"].get(m.split("/")[0], {})
    pairs = [p.split("=", 1) for p in cfg.split(",")]
    return ",".join(f"{k}={v}" for k, v in sorted((names.get(k, k), v) for k, v in pairs))


def keys(d):
    return {K.get(k, k): v for k, v in d.items()}


def series_meta(s):
    base = KM["base"][s["base"]]
    out = keys(s)
    out["base"] = base
    out["part"] = KM["part"][s["parte"]]
    out["variant"] = KM["variant"][s["variante"]]
    if base == "synthetic":
        out["name"] = KM["synthetic_type"][s["nome"]]
    names = KM["field_name"].get(base, {})
    if s.get("nomes") is not None:
        out["field_names"] = [names.get(x, x) for x in s["nomes"]]
    out["events"] = [dict(keys(e), extra=keys(e["extra"])) for e in s["eventos"]]
    out["extra"] = keys(s["extra"])
    return out


def detector_output(d):
    if d is None:
        return None
    reports = [{"t": r["t"], "fields": [dict(keys(c), **({"direction": KM["direction"][c["direcao"]]} if "direcao" in c else {})) for c in r["campos"]]}
               for r in d["relatos"]]
    events = []
    for e in d["eventos"]:
        n = keys(e); n["event"] = KM["trajectory_event"][e["evento"]]
        if "tipo" in e:
            n["kind"] = KM["record_kind"][e["tipo"]]
        events.append(n)
    return {"warnings": d["avisos"], "reports": reports, "events": events}


def translate(o):
    """One original series output in the current schema."""
    out = {"series": series_meta(o["serie"]),
           "methods": {method(m): {config(m, c): w for c, w in cs.items()} for m, cs in o["metodos"].items()},
           "detector": detector_output(o["detector"]),
           "seconds": {method(m): v for m, v in o["segundos"].items()},
           "not_run": {method(m): KM["not_run_reason"].get(v, v) for m, v in o["nao_rodado"].items()}}
    if "cjsd_registro" in o:
        out["cjsd_log"] = o["cjsd_registro"]
    return out


def series_key(o):
    m = o["series"]
    return f"{m['base']}|{m['variant']}|{m['name']}|{m['seed']}" + ("|calibration" if "cjsd_log" in o else "")


def read(folder, original):
    out = {}
    for f in sorted(glob.glob(os.path.join(folder, "**", "*.json.gz"), recursive=True)):
        with gzip.open(f, "rt", encoding="utf-8") as g:
            o = json.load(g)
        if original:
            o = translate(o)
        k = series_key(o)
        if k in out:
            raise SystemExit(f"two outputs for the series {k} in {folder}")
        out[k] = (f, o)
    return out


def differences(a, b):
    """The parts of two outputs (current schema) that differ, without the machine time."""
    out = []
    for part in ("series", "not_run", "cjsd_log"):
        if a.get(part) != b.get(part):
            out.append(part)
    ma, mb = a["methods"], b["methods"]
    for m in sorted(set(ma) | set(mb)):
        if m not in ma or m not in mb:
            out.append(f"methods/{m} (only in {'original' if m in ma else 'new'})"); continue
        for c in sorted(set(ma[m]) | set(mb[m])):
            if ma[m].get(c) != mb[m].get(c):
                out.append(f"methods/{m}/{c}" + ("" if c in ma[m] and c in mb[m] else " (missing on one side)"))
    da, db = a["detector"], b["detector"]
    if (da is None) != (db is None):
        out.append("detector (missing on one side)")
    elif da is not None:
        for k in sorted(set(da) | set(db)):
            if da.get(k) != db.get(k):
                out.append(f"detector/{k}")
    return out


def output_file_name(meta):
    sys.path.insert(0, ROOT)
    from runner.run import output_file_name as name
    return name(SimpleNamespace(base=meta["base"], name=meta["name"], variant=meta["variant"], seed=meta["seed"]))


def convert(orig, dest):
    n = 0; renamed = 0
    for f in sorted(glob.glob(os.path.join(orig, "**", "*.json.gz"), recursive=True)):
        rel = os.path.relpath(f, orig).split(os.sep)
        if len(rel) != 3:
            raise SystemExit(f"unexpected layout: {f}")
        with gzip.open(f, "rt", encoding="utf-8") as g:
            o = translate(json.load(g))
        base_dir = KM["base"][rel[0]]
        var = rel[1]; suffix = ""
        if var.endswith("_calibracao"):
            var, suffix = var[:-len("_calibracao")], "_calibration"
        folder = os.path.join(dest, base_dir, KM["variant"][var] + suffix); os.makedirs(folder, exist_ok=True)
        name = output_file_name(o["series"])
        renamed += name != rel[2]
        with gzip.open(os.path.join(folder, name), "wt", encoding="utf-8") as g:
            json.dump(o, g)
        n += 1
    lives = os.path.join(orig, "vidas")
    if os.path.isdir(lives) and not os.path.exists(os.path.join(dest, "lives")):
        os.symlink(os.path.abspath(lives), os.path.join(dest, "lives"))
    print(f"{n} outputs converted into {dest}; {renamed} with a file name different from the original one")
    return 0


def compare(orig, new, sample, show):
    A = read(orig, True); B = read(new, False)
    expected = [k for k in A if k in B] if sample else list(A)
    missing_new = [k for k in expected if k not in B]
    missing_orig = [k for k in B if k not in A]
    same = diff = 0; details = []
    for k in expected:
        if k not in B:
            continue
        d = differences(A[k][1], B[k][1])
        if d:
            diff += 1; details.append((k, d))
        else:
            same += 1
    print(f"series compared: {same + diff}; identical: {same}; different: {diff}; "
          f"missing in the new run: {len(missing_new)}; missing in the original run: {len(missing_orig)}")
    for k, d in details[:show]:
        print(f"  DIFFERENT {k}: {', '.join(d[:10])}{' ...' if len(d) > 10 else ''}")
    for k in missing_new[:show]:
        print(f"  MISSING IN NEW {k}")
    for k in missing_orig[:show]:
        print(f"  MISSING IN ORIGINAL {k}")
    return 1 if diff or missing_new or missing_orig else 0


def main():
    ap = argparse.ArgumentParser(description="Compares or converts the outputs of the approval run.")
    ap.add_argument("original"); ap.add_argument("other")
    ap.add_argument("--convert", action="store_true"); ap.add_argument("--sample", action="store_true"); ap.add_argument("--show", type=int, default=20)
    a = ap.parse_args()
    if a.convert:
        return convert(a.original, a.other)
    return compare(a.original, a.other, a.sample, a.show)


if __name__ == "__main__":
    sys.exit(main())
