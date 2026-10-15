"""The rows of the benchmark and the verdict of each (protocol, section 6), from the outputs of the runner.

python -m metrics.rows <run_folder> [--lives DIR] [--json rows.json]
  --lives  the folder with the lives of the simulated company used in the run (needed for the company rows M1 to M5)

Verdict of a row with competitors: against the best competitor of the row (the largest value of the main metric among all methods
and the configurations of each that respect the false-warning ceiling of the row's null; ties are broken by runner.configs
METHOD_ORDER), at 2 standard errors of the difference (paired resampling of the series, or of the episodes in the company). Row with
only the detector: against the row's null, and it only passes if it is above it by more than 2 standard errors. Declared limit row:
reported, outside the verdict. The detector's null above the ceiling fails the row.
The outputs are read in file-name order (runner.run.output_file_name); the company rows take the lives in the order in which they
first appear, and that order feeds the resampling."""
import argparse
import glob
import gzip
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from runner.configs import method_rank  # noqa: E402
from runner.series import Event  # noqa: E402
from metrics.events import aggregate, resample, score_series, se_binomial, verdict  # noqa: E402

REL = ["sea", "sea_large", "sea_gradual", "stagger", "num_real", "num_imbalanced", "num_noisy", "mc_real", "mc_cat"]
INP = ["cov", "cov_gradual", "num_cov", "cat_cov", "mc_cov", "slow_abrupt", "ramp_all"]
SLOW = ["slow_all", "slow_few"]
LIM = {"slow_real": "L1", "cat_real": "L2", "xor": "L3"}
NUL = ["null_sea", "null_num", "null_cat", "null_mc", "slow_null", "null_xor"]
CEILING_ALERT, CEILING_LOG, CEILING_PUBLIC, CEILING_COMPANY = 0.02, 0.05, 0.1, 0.3
T, N = 10000, 20000
DET = ("detector", "default")
PUBLIC = {"nab": ("P1", "NAB"), "smd": ("P4", "SMD"), "smap": ("P5", "SMAP"), "msl": ("P6", "MSL")}


def read(folder):
    out = []
    for f in sorted(glob.glob(os.path.join(folder, "**", "*.json.gz"), recursive=True)):
        if os.path.basename(os.path.dirname(f)).endswith("_calibration"):   # only the CJSD log for the default thresholds; not a run
            continue
        with gzip.open(f, "rt", encoding="utf-8") as g:
            out.append(json.load(g))
    return out


def events_of(meta):
    return [Event(e["start"], e["end"], tuple(e["window"]), None if e["fields"] is None else frozenset(e["fields"]), e["kind"], e["mark"], e["extra"])
            for e in meta["events"]]


def variants(outputs):
    """(method, cfg) present in every output, in the fixed method order."""
    vs = None
    for o in outputs:
        cur = {(m, c) for m, cs in o["methods"].items() for c in cs}
        vs = cur if vs is None else vs & cur
    return sorted(vs or [], key=method_rank)


def count(o, method, cfg, kind=None, events=None, start=None, end=None):
    m = o["series"]; av = o["methods"][method][cfg]
    return score_series(events_of(m) if events is None else events, av, m["score_start"] if start is None else start,
                        m["n"] if end is None else end, kind, [tuple(x) for x in m["ignore"]], m["minutes_per_item"], 500, m["d"])


def method_kinds(method):
    if method.endswith("/error"):
        return {"REAL"}
    if method in ("detector", "cjsd", "watch", "ctm"):
        return {"REAL", "VIRTUAL"}
    return {"VIRTUAL"}


def best(values, eligible):
    """The best competitor: the largest value; among equal values, the one later in the fixed method order."""
    cand = [(v, method_rank(k), k) for k, v in values.items() if k[0] != "detector" and k in eligible and v is not None and np.isfinite(v)]
    if not cand:
        return None, None
    v, _, k = max(cand)
    return v, k


def _one(detected):
    return {"events": 1, "detected": int(detected), "false": 0, "items": 0, "days": None, "latencies": [], "when": [], "when_ok": 0,
            "field_n": 0, "field_precise": 0, "field_cover": 0}


def row_with_competitors(name, per_var, key, eligible, det_null_ok, limit=None, info=None):
    """per_var: {(method, cfg): [counts per series, same order]}."""
    val = {k: aggregate(v)[key] for k, v in per_var.items()}
    det = val.get(DET); best_v, best_k = best(val, eligible)
    se = None
    if best_k is not None:
        rs = resample({"d": per_var[DET], "c": per_var[best_k]}, key)
        dif = rs["d"] - rs["c"]; se = float(np.nanstd(dif))
    v = verdict(det if det is not None else 0.0, best_v, se)
    if not det_null_ok:
        status = "FAILED (detector's null above the ceiling)"
    elif limit:
        status = f"limit {limit} " + ("confirmed" if v == "LOST" else "not confirmed in this sample")
    else:
        status = "PASSED" if v in ("WON", "TIED", "NO COMPETITOR") else "FAILED"
    ag = {f"{k[0]}|{k[1]}": aggregate(v_) for k, v_ in per_var.items()}
    return {"row": name, "metric": key, "detector": det, "best_competitor": None if best_k is None else f"{best_k[0]}|{best_k[1]}",
            "best_value": best_v, "se_difference": se, "verdict": v, "status": status, "limit": limit, "info": info or {}, "per_method": ag}


def row_against_null(name, k, n, k0, n0, info=None, limit=None):
    if not n or not n0:
        return {"row": name, "detector": k / n if n else None, "n": n, "null": None, "n_null": n0, "se_difference": None,
                "verdict": "NO DATA" if not n else "NULL NOT MEASURED", "status": "no verdict (n = 0 in the row or in the null)", "info": info or {}}
    p = k / n if n else None; p0 = k0 / n0 if n0 else None
    se = math.sqrt((se_binomial(k, n) or 0) ** 2 + (se_binomial(k0, n0) or 0) ** 2) if n and n0 else None
    above = p is not None and p0 is not None and p - p0 > 2 * (se or 0)
    status = (f"limit {limit} " + ("confirmed" if not above else "not confirmed in this sample")) if limit else ("PASSED" if above else "FAILED")
    return {"row": name, "detector": p, "n": n, "null": p0, "n_null": n0, "se_difference": se, "verdict": "ABOVE NULL" if above else "NOT ABOVE NULL",
            "status": status, "info": info or {}}


# ------------------------------------------------------------------ synthetic
def _true_size(stream, a, b, x0, x1):
    """The true displacement (in standard deviations of the field) between the "before" window [a, b) and the "after" window
    [x0, x1), from the generators."""
    t = np.arange(N)
    if stream in ("cov", "cov_gradual"):
        p = (t >= T).astype(float) if stream == "cov" else np.clip((t - T) / 2000, 0, 1); s = 2.0 * p; sd = 10 / math.sqrt(12)
    elif stream in ("num_cov", "mc_cov"):
        s = (t >= T).astype(float); sd = 1.0
    elif stream == "slow_abrupt":
        s = t / N + (t >= T); sd = 1.0
    elif stream == "ramp_all":
        s = 0.5 * np.clip((t - T) / 2000, 0, 1); sd = 1.0
    else:
        return None
    a, b, x0, x1 = (max(0, min(N, v)) for v in (a, b, x0, x1))
    if b <= a or x1 <= x0:
        return None
    return float((s[x0:x1].mean() - s[a:b].mean()) / sd)


def synthetic(outputs):
    by_stream = defaultdict(list)
    for o in outputs:
        m = o["series"]; by_stream[(m["name"], m["variant"])].append(o)
    for v in by_stream.values():
        v.sort(key=lambda o: o["series"]["seed"])
    nulls = [o for (f, var), os_ in by_stream.items() for o in os_ if f in NUL or var == "shuffled"]
    vs = sorted({(m, c) for o in outputs for m, cs in o["methods"].items() for c in cs}, key=method_rank)

    def null_ok(k, kind, ceiling):
        ns = [o for o in nulls if k[0] in o["methods"] and k[1] in o["methods"][k[0]]]
        if not ns:
            return True
        r = sum(any(a[1] == kind and a[0] >= o["series"]["score_start"] for a in o["methods"][k[0]][k[1]]) for o in ns)
        return r / len(ns) <= ceiling

    null_alert = {k: null_ok(k, "REAL", CEILING_ALERT) for k in vs}; null_log = {k: null_ok(k, "VIRTUAL", CEILING_LOG) for k in vs}
    rows = []
    sel = lambda streams: [o for f in streams for o in by_stream.get((f, "main"), [])]
    # S1 relation breaks (alert)
    rel = sel(REL)
    if rel:
        pv = {k: [count(o, k[0], k[1], "REAL") for o in rel] for k in variants(rel)}
        rows.append(row_with_competitors("S1 relation breaks: alert", pv, "f1", {k for k in vs if null_alert[k]}, null_alert[DET]))
    # S2 input changes (log), with the undue alerts of the detector
    inp = sel(INP)
    if inp:
        pv = {k: [count(o, k[0], k[1], "VIRTUAL") for o in inp] for k in variants(inp)}
        undue = {f: sum(any(a[1] == "REAL" and a[0] >= T for a in o["methods"]["detector"]["default"]) for o in by_stream.get((f, "main"), [])) for f in INP}
        n_f = {f: len(by_stream.get((f, "main"), [])) for f in INP}
        ok_undue = all(undue[f] <= 0.10 * n_f[f] for f in INP if n_f[f])
        L = row_with_competitors("S2 input changes: log", pv, "f1", {k for k in vs if null_log[k]}, null_log[DET] and ok_undue,
                                 info={"detector_undue_alert": {f: f"{undue[f]}/{n_f[f]}" for f in INP}})
        if not ok_undue:
            L["status"] = "FAILED (detector's undue alert above 10% in one stream)"
        rows.append(L)
    # S3 where: detection with the right field (only the methods that name a field)
    with_field = [(o, "REAL") for o in rel] + [(o, "VIRTUAL") for o in inp]
    with_field = [(o, tp) for o, tp in with_field if o["series"]["events"] and o["series"]["events"][0]["fields"]]
    if with_field:
        def hit(o, k, tp):
            c = count(o, k[0], k[1], tp); p = c["per_event"][0]; v = set(o["series"]["events"][0]["fields"])
            return _one(p is not None and bool(p[2]) and set(p[2]) <= v)
        names_field = {k for k in vs if not k[0].endswith("/error") and k[0] not in ("cjsd", "watch", "ctm", "isolation_forest")}
        pv = {k: [hit(o, k, tp) for o, tp in with_field] for k in variants([o for o, _ in with_field]) if k in names_field}
        rows.append(row_with_competitors("S3 where: detection with the right field, among N", pv, "sensitivity",
                                         {k for k in pv if null_alert[k] and null_log[k]}, null_alert[DET] and null_log[DET],
                                         info={"N": "3 (sea, stagger, cov), 10 (xor), 20 (the others)"}))
    # S4 what (only the detector gives direction, size and trajectory)
    dir_ok = dir_n = size_ok = size_n = nn_ok = nn_n = 0; truths = []
    for f in INP:
        for o in by_stream.get((f, "main"), []):
            ev = o["series"]["events"][0]; v = set(ev["fields"]); d = o["detector"]
            av = [a for a in d["warnings"] if a[1] == "VIRTUAL" and ev["window"][0] <= a[0] < ev["window"][1]]
            if av:
                a = av[0]; rep = next((r for r in d["reports"] if r["t"] == a[0]), None)
                if rep:
                    for c in rep["fields"]:
                        if c["field"] not in v:
                            continue
                        if "direction" in c:
                            dir_n += 1; dir_ok += c["direction"] == "up"
                            since = a[3] if a[3] is not None else a[0]; tr = a[0] + 500
                            vt = _true_size(f, since - 1000, since, max(since, tr - 499), tr + 1)
                            if vt is not None and "size_sd" in c:
                                size_n += 1; size_ok += abs(c["size_sd"] - vt) <= 0.25; truths.append(vt)
                        elif "value" in c:
                            dir_n += 1; dir_ok += c["value"] == 0.0 and c["share_after"] > c["share_before"]
                        break
            if f != "cat_cov":
                nn_n += 1
                nn_ok += any(e["event"] == "became_new_normal" and e["field"] in v and e["t"] >= T for e in d["events"])
    med = float(np.median(truths)) if truths else 0.0
    size_null = sum(abs(med - vt) <= 0.25 for vt in truths)
    null_nn = sum(any(e["event"] == "became_new_normal" for e in o["detector"]["events"]) for o in nulls if o["series"]["variant"] == "main")
    n_null = sum(1 for o in nulls if o["series"]["variant"] == "main")
    rows += [row_against_null("S4a what: right direction", dir_ok, dir_n, dir_n / 2, dir_n),
             row_against_null("S4b what: size within 0.25 sd", size_ok, size_n, size_null, size_n,
                              info={"null": f"constant guess = the median of the true sizes ({med:.2f} sd)"}),
             row_against_null("S4c what: became the new normal on the steps that stay", nn_ok, nn_n, null_nn, n_null,
                              info={"null": "null streams with some new normal"})]
    # S5 slow drift kept (in the log and no alert)
    slow = sel(SLOW)
    if slow:
        def keeps(o, k):
            av = [a for a in o["methods"][k[0]][k[1]] if a[0] >= o["series"]["score_start"]]
            return _one((not any(a[1] == "REAL" for a in av)) and any(a[1] == "VIRTUAL" for a in av))
        pv = {k: [keeps(o, k) for o in slow] for k in variants(slow)}
        rows.append(row_with_competitors("S5 slow drift: in the log and no alert", pv, "sensitivity", {k for k in vs if null_alert[k]}, null_alert[DET]))
    # S6 declared limits (reported, outside the verdict)
    for f, lim in LIM.items():
        os_ = by_stream.get((f, "main"), [])
        if os_:
            pv = {k: [count(o, k[0], k[1], "REAL") for o in os_] for k in variants(os_)}
            rows.append(row_with_competitors(f"S6 declared limit {lim}: {f}", pv, "f1", {k for k in vs if null_alert[k]}, True, limit=lim))
    # S7 nulls: the ceiling of the detector
    if nulls:
        with_kind = lambda o, k, kind: any(a[1] == kind and a[0] >= o["series"]["score_start"] for a in o["methods"][k[0]][k[1]])
        ra = sum(with_kind(o, DET, "REAL") for o in nulls)
        rl = sum(with_kind(o, DET, "VIRTUAL") for o in nulls)
        ok = ra <= CEILING_ALERT * len(nulls) and rl <= CEILING_LOG * len(nulls)
        per = {f"{k[0]}|{k[1]}": {"runs_with_alert": sum(with_kind(o, k, "REAL") for o in nulls),
                                  "runs_with_log": sum(with_kind(o, k, "VIRTUAL") for o in nulls)} for k in variants(nulls)}
        rows.append({"row": "S7 nulls: runs with a warning (ceiling: alert 2%, log 5%)", "detector": {"alert": f"{ra}/{len(nulls)}", "log": f"{rl}/{len(nulls)}"},
                     "status": "PASSED" if ok else "FAILED", "per_method": per, "n": len(nulls)})
    return rows


# ------------------------------------------------------------------ public bases
def public(outputs, base, variant="main"):
    code, label = PUBLIC[base]
    orig = sorted([o for o in outputs if o["series"]["base"] == base and o["series"]["variant"] == variant], key=lambda o: o["series"]["name"])
    orig = [o for o in orig if o["series"]["n"] > o["series"]["warmup"]]
    shuf = [o for o in outputs if o["series"]["base"] == base and o["series"]["variant"] == "shuffled"]
    vs = variants(orig)
    null = {}; null_parts = {}
    for k in vs:
        f = i = 0
        for o in shuf:
            if k[0] not in o["methods"] or k[1] not in o["methods"][k[0]]:
                continue
            f += sum(1 for a in o["methods"][k[0]][k[1]] if a[0] >= o["series"]["warmup"]); i += o["series"]["n"] - o["series"]["warmup"]
        fs, is_ = f, i
        for o in orig:
            a_, b_ = o["series"]["extra"].get("train_null", (0, 0))
            if b_ > a_:
                f += sum(1 for a in o["methods"][k[0]][k[1]] if a_ <= a[0] < b_); i += b_ - a_
        null[k] = 1000.0 * f / i if i else None          # None: not measured (in development the grid does not run on the shuffled series)
        null_parts[k] = {"shuffled": 1000.0 * fs / is_ if is_ else None, "train": 1000.0 * (f - fs) / (i - is_) if i > is_ else None}
    ok = lambda k: null[k] is None or null[k] <= CEILING_PUBLIC   # a competitor with an unmeasured null stays eligible (the doubt is in its favor)
    det_ok = null[DET] is not None and null[DET] <= CEILING_PUBLIC

    def split(o):
        """The events that decide and those shorter than 10 items (limit L4); the windows of the latter are ignored in the row that
        decides. NAB marks windows around labeled points, not event durations: no NAB event counts as short."""
        evs = events_of(o["series"]); short = [e for e in evs if (e.end - e.start) < 10 and base != "nab"]
        return [e for e in evs if e not in short], short

    def count_main(o, k):
        dec, short = split(o); m = o["series"]
        ig = [tuple(x) for x in m["ignore"]] + [(e.window[0], e.window[1], None) for e in short]
        return score_series(dec, o["methods"][k[0]][k[1]], m["score_start"], m["n"], None, ig, m["minutes_per_item"], 500, m["d"])

    pv = {k: [count_main(o, k) for o in orig] for k in vs}
    if variant == "main":
        name = f"{code} {label}"
    else:
        name = f"{code}c {label} ({variant}, information only)"
    L = row_with_competitors(name + ": event F1", pv, "f1", {k for k in vs if ok(k)}, (variant != "main") or det_ok,
                             info={"null_warnings_per_1000": {f"{k[0]}|{k[1]}": None if v is None else round(v, 4) for k, v in null.items()},
                                   "null_by_part": {f"{k[0]}|{k[1]}": v for k, v in null_parts.items()},
                                   "out_of_reach": sum(o["series"]["out_of_reach"] for o in orig), "series": len(orig)})
    if variant != "main":
        L["status"] = "information only"
    out = [L]
    if variant == "main":
        l4 = f"{code}L4 {label}: events shorter than 10 items (limit L4)"
        short_total = sum(len(split(o)[1]) for o in orig)
        info = {"events": short_total}
        if base == "nab":
            info["note"] = "NAB marks windows around labeled points, not event durations; no NAB event is counted as shorter than 10 items"
        if short_total:
            def count_l4(o, k):
                dec, short = split(o); m = o["series"]
                return score_series(short, o["methods"][k[0]][k[1]], m["score_start"], m["n"], None, [], m["minutes_per_item"], 500, m["d"])
            pv4 = {k: [count_l4(o, k) for o in orig] for k in vs}
            L4 = row_with_competitors(l4, pv4, "sensitivity", {k for k in vs if ok(k)}, True, limit="L4", info=info)
            L4["n"] = short_total
        else:
            L4 = {"row": l4, "metric": "sensitivity", "detector": None, "n": 0, "best_competitor": None, "best_value": None,
                  "se_difference": None, "verdict": "NO DATA", "status": "limit L4 not measured (n = 0)", "limit": "L4", "info": info}
        out.append(L4)
    if base == "smd" and variant == "main":
        def fields(o, k):
            c = count_main(o, k); evs, _ = split(o); ok_ = cov = 0.0
            for e, p in zip(evs, c["per_event"]):
                if p is not None and p[2] and e.fields:
                    s, v = set(p[2]), set(e.fields); ok_ += s <= v; cov += len(s & v) / len(v)
            return {"events": len(evs), "detected": int(ok_), "false": 0, "items": 0, "days": None, "latencies": [], "when": [], "when_ok": 0,
                    "field_n": 0, "field_precise": 0, "field_cover": cov}
        names_field = {k for k in vs if k[0] not in ("cjsd", "watch", "ctm", "isolation_forest")}
        pv2 = {k: [fields(o, k) for o in orig] for k in vs if k in names_field}
        out.append(row_with_competitors(f"{code}o {label} where: detection with the right fields, among 38", pv2, "sensitivity",
                                        {k for k in names_field if ok(k)}, det_ok))
    return out


# ------------------------------------------------------------------ the simulated company
DAY = 1440


def company(outputs, lives):
    from runner.company import LATENCY_FIELD, read_truth
    by_life = defaultdict(dict)
    for o in outputs:
        if o["series"]["base"] == "company" and o["series"]["variant"] == "main":
            by_life[o["series"]["extra"]["life"]][o["series"]["extra"]["process"]] = o
    if not by_life:
        return []
    V = {nv: json.load(open(os.path.join(lives, nv, "verdade.json"), encoding="utf-8")) for nv in by_life}
    TR = {nv: read_truth(V[nv], V[nv].get("nulo")) for nv in by_life}
    vs = variants([o for nv in by_life if V[nv].get("nulo") is None for o in by_life[nv].values()])
    granular = lambda k: k[0] not in ("cjsd", "watch", "isolation_forest")       # the others only name the process

    def warnings(nv, k, where):
        """(minute of the warning, minute of the attributed start) on the field where = [process, field]; a method without fields:
        the warnings on the process."""
        o = by_life[nv].get(where[0])
        if o is None or where[1] not in o["series"]["field_names"] or k[0] not in o["methods"] or k[1] not in o["methods"][k[0]]:
            return []
        j = o["series"]["field_names"].index(where[1]); out = []
        for a in o["methods"][k[0]][k[1]]:
            if k[0] == "detector" and a[1] != "VIRTUAL":
                continue
            if a[0] < o["series"]["score_start"]:
                continue
            if (granular(k) and j in a[2]) or (not granular(k)):
                out.append((a[0] + 1, (a[3] if a[3] is not None else a[0]) + 1))
        return out

    def trajectory_events(nv, where, name):
        o = by_life[nv].get(where[0])
        if o is None or where[1] not in o["series"]["field_names"]:
            return []
        j = o["series"]["field_names"].index(where[1])
        return [e["t"] + 1 for e in o["detector"]["events"] if e["field"] == j and e["event"] == name]

    normal = [nv for nv in by_life if V[nv].get("nulo") is None]
    no_defect = [nv for nv in by_life if V[nv].get("nulo") == "sem_defeito"]
    no_drift = [nv for nv in by_life if V[nv].get("nulo") == "sem_deriva"]
    rows = []
    # M1 contingency: warning on the error field of the affected route within 60 minutes of the defective release
    eps = [(nv, lb) for nv in normal for lb in TR[nv]["releases"] if lb["defect"]]
    routes = sorted({tuple(x) for _, lb in eps for x in [lb["where"][0]] + lb["alternatives"]})
    null_releases = [(nv, lb) for nv in no_defect for lb in TR[nv]["releases"]]
    pv, null = {}, {}
    for k in vs:
        pv[k] = [_one(any(lb["t"] <= m <= lb["t"] + 60 for x in [lb["where"][0]] + lb["alternatives"] for m, _ in warnings(nv, k, x))) for nv, lb in eps]
        f = sum(any(lb["t"] <= m <= lb["t"] + 60 for x in routes for m, _ in warnings(nv, k, list(x))) for nv, lb in null_releases)
        null[k] = f / len(null_releases) if null_releases else 0.0
    if eps:
        w_ok = w_n = 0
        for nv, lb in eps:
            for x in [lb["where"][0]] + lb["alternatives"]:
                av = [(m, since) for m, since in warnings(nv, DET, x) if lb["t"] <= m <= lb["t"] + 60]
                if av:
                    w_n += 1; pe = lb["first_error"] or lb["t"]; w_ok += pe - 30 <= av[0][1] <= pe + 10; break
        rows.append(row_with_competitors("M1 contingency: warning on the route's error field within 60 min", pv, "sensitivity",
                                         {k for k in vs if null[k] <= CEILING_COMPANY}, null[DET] <= CEILING_COMPANY,
                                         info={"episodes": len(eps), "releases_in_null": len(null_releases), "null": {f"{k[0]}|{k[1]}": round(v, 3) for k, v in null.items()},
                                               "granularity": "process for cjsd, watch and isolation_forest",
                                               "detector_when": f"{w_ok}/{w_n} with the start in [first error - 30, + 10]"}))
    # M2 incident: warning on the probe within 10 minutes, with the attributed start between 30 minutes before and 10 after
    incs = [(nv, i) for nv in by_life for i in TR[nv]["incidents"]]
    if incs:
        g = np.random.default_rng(20261012); null_windows = []
        for nv in sorted(by_life):
            bad = [(i["start"] - 60, i["end"] + 60) for i in TR[nv]["incidents"]]
            cand = [int(x) for x in g.integers(2001, V[nv]["minutos"] - 10, 400) if not any(a <= x <= b for a, b in bad)][:200]
            null_windows += [(nv, x) for x in cand]
        pv, null = {}, {}
        probe = ["sonda de disponibilidade", "verificações com falha no minuto"]
        for k in vs:
            pv[k] = [_one(any(i["start"] <= m <= i["start"] + 10 and i["start"] - 30 <= since <= i["start"] + 10 for m, since in warnings(nv, k, probe)))
                     for nv, i in incs]
            null[k] = sum(any(x <= m <= x + 10 for m, _ in warnings(nv, k, probe)) for nv, x in null_windows) / max(1, len(null_windows))
        rows.append(row_with_competitors("M2 incident: warning on the probe within 10 min and start attributed inside the window", pv, "sensitivity",
                                         {k for k in vs if null[k] <= CEILING_COMPANY}, null[DET] <= CEILING_COMPANY,
                                         info={"incidents": len(incs), "null_windows": len(null_windows), "null": {f"{k[0]}|{k[1]}": round(v, 3) for k, v in null.items()}}))
    # M3 regime change: became the new normal on the latency field within 15 days (only the detector has trajectories)
    k3 = n3 = k30 = n30 = 0
    for nv in by_life:
        lat = {tuple(x) for m in TR[nv]["regime_changes"] for x in m["where"]}
        every = [(p, c) for p, o in by_life[nv].items() for c in o["series"]["field_names"] if p.startswith("rota ") and c == LATENCY_FIELD]
        for m in TR[nv]["regime_changes"]:
            for x in m["where"]:
                n3 += 1; k3 += any(m["t"] <= t <= m["t"] + 15 * DAY for t in trajectory_events(nv, x, "became_new_normal"))
            for x in every:
                if x not in lat:
                    n30 += 1; k30 += any(m["t"] <= t <= m["t"] + 15 * DAY for t in trajectory_events(nv, list(x), "became_new_normal"))
    rows.append(row_against_null("M3 regime change: became the new normal within 15 days", k3, n3, k30, n30,
                                 info={"null": "latency fields of routes without a regime change, in the same windows"}))
    # M4 drift: the portfolio becomes the new normal in the normal lives and never in the no-drift null
    portfolio = ["carteira de clientes", "clientes ativos"]
    nn_normal = [len(trajectory_events(nv, portfolio, "became_new_normal")) for nv in normal]
    nn_no_drift = [len(trajectory_events(nv, portfolio, "became_new_normal")) for nv in no_drift]
    ok4 = bool(nn_normal) and all(x >= 1 for x in nn_normal) and all(x == 0 for x in nn_no_drift)
    rows.append({"row": "M4 drift: the portfolio becomes the new normal in the normal lives and never without drift",
                 "detector": {"normal": nn_normal, "no_drift": nn_no_drift}, "status": "PASSED" if ok4 else "FAILED"})
    # M5 return: the episode of the error field returns to normal within 180 minutes after the defect goes off the air
    k5 = n5 = 0; delay5 = []
    for nv, lb in eps:
        if not lb.get("off_air"):
            continue
        for x in [lb["where"][0]] + lb["alternatives"]:
            if any(lb["t"] <= m <= lb["t"] + 60 for m, _ in warnings(nv, DET, x)):
                back = [t for t in trajectory_events(nv, x, "returned_to_normal") if t >= lb["off_air"]]
                delay5.append(min(back) - lb["off_air"] if back else None)
                n5 += 1; k5 += any(lb["off_air"] <= t <= lb["off_air"] + 180 for t in back); break
    k50 = n50 = 0
    for nv in no_defect:
        for x in routes:
            for a in trajectory_events(nv, list(x), "opened"):
                n50 += 1; k50 += any(a + 60 <= t <= a + 240 for t in trajectory_events(nv, list(x), "returned_to_normal"))
    rows.append(row_against_null("M5 return: back to normal within 180 min after the outage", k5, n5, k50, n50,
                                 info={"null": "episodes opened on the route error fields in the no-defect null: returned between 60 and 240 min after opening",
                                       "minutes_to_return_after_off_air": delay5}))
    return rows


def benchmark_verdict(rows):
    """The benchmark passes if every row that decides passed; limit and information rows do not decide; a row that decides without
    data does not pass (protocol, section 6)."""
    decide = [L for L in rows if not L["status"].startswith(("limit", "information only"))]
    failed = [L["row"] for L in decide if not L["status"].startswith("PASSED")]
    return {"status": "FAILED" if failed or not decide else "PASSED", "rows_that_decide": len(decide), "not_passed": failed}


def main():
    ap = argparse.ArgumentParser(description="The rows of the benchmark and the verdict of each.")
    ap.add_argument("run"); ap.add_argument("--lives", default=None); ap.add_argument("--json", default=None)
    a = ap.parse_args()
    outputs = read(a.run); rows = []
    synth = [o for o in outputs if o["series"]["base"] == "synthetic"]
    if synth:
        rows += synthetic(synth)
    for base in ("nab", "smd", "smap", "msl"):
        for var in ("main", "warmup500"):
            if any(o["series"]["base"] == base and o["series"]["variant"] == var for o in outputs):
                rows += public(outputs, base, var)
    if a.lives:
        rows += company(outputs, a.lives)
    for L in rows:
        det = L.get("detector"); det = f"{det:.3f}" if isinstance(det, float) else det
        print(f"{L['row']:75s} detector {det}  best {L.get('best_competitor')} {L.get('best_value')}  {L.get('verdict', '')}  -> {L['status']}")
    vb = benchmark_verdict(rows)
    print(f"benchmark: {vb['status']} ({vb['rows_that_decide']} rows decide; not passed: {', '.join(vb['not_passed']) or 'none'})")
    if a.json:
        json.dump(rows, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)


if __name__ == "__main__":
    main()
