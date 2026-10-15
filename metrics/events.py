"""The event metrics of the benchmark (protocol, section 5). No "point adjust": an event is detected when there is at least one
warning inside its tolerance window; a warning outside every window (and outside the stretches declared as ignored) is false; several
warnings in the same window count one event. No point metric is used.

score_series returns the counts of one series; aggregate sums the counts of several series and computes precision, sensitivity, F1,
false warnings per 1,000 items and per day, latency, when and field; resample gives the standard error by paired resampling of the
series."""
import math

import numpy as np


def score_series(events, warnings, start, end, kind=None, ignore=(), minutes_per_item=None, when_tolerance=None, n_fields=None):
    """events: list of Event (window [a, b), start, mark, fields); warnings: [t, kind, fields, since]; start and end: the scored
    stretch. kind: only the warnings of that kind count (None: all). ignore: (a, b, kind) stretches where warnings of that kind are
    not false."""
    av = [a for a in warnings if start <= a[0] < end and (kind is None or a[1] == kind)]
    used = set(); det = 0; lat = []; when = []; when_ok = 0; field_precise = field_cover = field_n = 0
    per_event = []
    for e in events:
        a_, b_ = e.window
        inside = [i for i, a in enumerate(av) if a_ <= a[0] < b_]
        used.update(inside)
        if not inside:
            per_event.append(None); continue
        det += 1; p = av[inside[0]]; ref = e.mark if e.mark is not None else e.start
        lat.append(p[0] - ref)
        since = p[3] if p[3] is not None else p[0]
        when.append(abs(since - e.start))
        if when_tolerance is not None:
            when_ok += abs(since - e.start) <= when_tolerance
        if e.fields is not None and p[2]:
            field_n += 1; s = set(p[2]); field_precise += s <= set(e.fields); field_cover += bool(s & set(e.fields))
        per_event.append(p)
    false = 0
    for i, a in enumerate(av):
        if i in used:
            continue
        if any(x <= a[0] < y and (tp is None or a[1] == tp) for x, y, tp in ignore):
            continue
        false += 1
    items = max(0, end - start)
    return {"events": len(events), "detected": det, "false": false, "warnings": len(av), "items": items,
            "days": (items * minutes_per_item / 1440.0) if minutes_per_item else None, "latencies": lat, "when": when,
            "when_ok": when_ok, "field_n": field_n, "field_precise": field_precise, "field_cover": field_cover, "n_fields": n_fields,
            "per_event": per_event}


def aggregate(counts):
    E = sum(c["events"] for c in counts); D = sum(c["detected"] for c in counts); F = sum(c["false"] for c in counts)
    items = sum(c["items"] for c in counts); days = [c["days"] for c in counts if c["days"] is not None]
    lat = [x for c in counts for x in c["latencies"]]; wh = [x for c in counts for x in c["when"]]
    fn = sum(c["field_n"] for c in counts)
    prec = D / (D + F) if (D + F) else (1.0 if E == 0 else 0.0)
    sens = D / E if E else None
    f1 = (2 * prec * sens / (prec + sens) if (prec + sens) else 0.0) if sens is not None else None
    return {"events": E, "detected": D, "false": F, "precision": prec, "sensitivity": sens, "f1": f1,
            "false_per_1000": 1000.0 * F / items if items else None,
            "false_per_day": (F / sum(days)) if days and len(days) == len(counts) and sum(days) > 0 else None,
            "median_latency": float(np.median(lat)) if lat else None,
            "latency_quartiles": [float(np.percentile(lat, 25)), float(np.percentile(lat, 75))] if lat else None,
            "median_when": float(np.median(wh)) if wh else None,
            "when_ok": sum(c["when_ok"] for c in counts),
            "field_n": fn, "field_precise": sum(c["field_precise"] for c in counts), "field_cover": sum(c["field_cover"] for c in counts),
            "items": items, "series": len(counts)}


def se_binomial(k, n):
    """Binomial standard error of a proportion: sqrt(p(1 - p)/n)."""
    if not n:
        return None
    p = k / n
    return math.sqrt(p * (1 - p) / n)


def resample(per_method, key="f1", n=1000, seed=20261012):
    """per_method: {method: [counts per series, in the same order of series]}. Returns {method: [value of the metric in each
    resample]}, with the same series drawn for every method (paired)."""
    names = list(per_method); k = len(per_method[names[0]])
    g = np.random.default_rng(seed); out = {m: [] for m in names}
    for _ in range(n):
        idx = g.integers(0, k, k)
        for m in names:
            v = aggregate([per_method[m][i] for i in idx])[key]
            out[m].append(np.nan if v is None else v)
    return {m: np.array(v) for m, v in out.items()}


def verdict(det, comp, se_dif):
    """WON if the detector is above the best competitor by more than 2 standard errors of the difference; LOST if below by more than
    2; TIED otherwise."""
    if comp is None:
        return "NO COMPETITOR"
    dif = det - comp
    if se_dif is None or not np.isfinite(se_dif):
        se_dif = 0.0
    if dif > 2 * se_dif:
        return "WON"
    if dif < -2 * se_dif:
        return "LOST"
    return "TIED"
