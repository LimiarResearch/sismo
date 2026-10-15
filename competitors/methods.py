"""The methods of the benchmark, all with the same interface: run(method, series, cfg, cache) -> list of warnings [t, kind, fields, since].
kind: "REAL" (alert: the relation between fields and response broke) or "VIRTUAL" (log: the input changed); fields: the accused field
indices ([] if the method does not name a field); since: the start the method attributes to the change (None if it does not estimate
one; the item of the warning is used then).

Common rules (protocol, section 4):
- every method learns from the same warm-up, the first series.warmup items, and receives the whole series from item 0; a warning
  inside the warm-up does not count (the method may restart because of it);
- per field: the method runs on each field, on the value standardized by the mean and standard deviation of the field in the
  warm-up (a standard deviation of 0 becomes 1);
- marks less than R_MERGE items after the previous one, from the same method on the same series, belong to the same warning (the
  first one), with the union of the fields;
- with a response (synthetic streams), the stream detectors also run on the 0/1 error of a streaming logistic regression (river;
  SoftmaxRegression with more than two classes): mode "error", warning = alert, no field;
- declared adapters: DDM and HDDM per field receive the 0/1 indicator "value outside the 0.5% to 99.5% range of the warm-up"; CJSD
  without a response uses only the input axis; WATCH without a response uses only the input martingale (X-CTM), and CTM is then the
  same method (it does not apply); WATCH, CTM and CJSD start over after each warning with a new warm-up (the following items), like
  the per-field test."""
import contextlib
import io
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
R_MERGE = 10


# ------------------------------------------------------------------ common pieces
def merge(marks, kind="VIRTUAL", R=R_MERGE):
    """marks: (t, field or None, since or None). Merges the marks that are less than R items after the previous one."""
    out = []; last = None
    for t, j, since in sorted(marks, key=lambda m: (m[0], -1 if m[1] is None else m[1])):
        if out and t - last < R:
            if j is not None and j not in out[-1][2]:
                out[-1][2].append(int(j))
            if since is not None:
                out[-1][3] = int(since) if out[-1][3] is None else min(out[-1][3], int(since))
        else:
            out.append([int(t), kind, [] if j is None else [int(j)], None if since is None else int(since)])
        last = t
    for a in out:
        a[2].sort()
    return out


def standardize(X, n0):
    mu = X[:n0].mean(0); sd = X[:n0].std(0); sd = np.where(sd > 0, sd, 1.0)
    return (X - mu) / sd


def outside_indicator(X, n0):
    lo = np.quantile(X[:n0], 0.005, axis=0); hi = np.quantile(X[:n0], 0.995, axis=0)
    return ((X < lo) | (X > hi)).astype(int)


def model_error(series, cache):
    """The 0/1 error of a streaming logistic regression (streaming standardization), item by item: 1 if the prediction made before
    seeing y is wrong."""
    if cache is not None and "error" in cache:
        return cache["error"]
    from river import compose, linear_model, preprocessing
    m = compose.Pipeline(preprocessing.StandardScaler(), linear_model.LogisticRegression() if series.K == 2 else linear_model.SoftmaxRegression())
    e = np.zeros(series.n)
    for t in range(series.n):
        x = {f"x{j}": float(v) for j, v in enumerate(series.X[t])}
        e[t] = int(m.predict_one(x) != series.y[t]) if t > 0 else 1
        m.learn_one(x, int(series.y[t]))
    if cache is not None:
        cache["error"] = e
    return e


# ------------------------------------------------------------------ stream detectors (river, fast KSWIN, CUSUM, EWMA)
def _factory(name, cfg):
    from river import drift
    from river.drift import binary
    from competitors.kswin_fast import FastKSWIN
    if name == "page_hinkley":
        return lambda: drift.PageHinkley(min_instances=cfg.get("min_instances", 30), delta=cfg.get("delta", 0.005), threshold=cfg.get("threshold", 50.0), alpha=1 - 0.0001)
    if name == "adwin":
        return lambda: drift.ADWIN(delta=cfg.get("delta", 0.002))
    if name == "kswin":
        return lambda: FastKSWIN(alpha=cfg.get("alpha", 0.005), window_size=cfg.get("window_size", 100), stat_size=cfg.get("stat_size", 30), seed=1)
    if name == "ddm":
        dt = cfg.get("drift_threshold", 3.0)
        return lambda: binary.DDM(warm_start=cfg.get("warm_start", 30), warning_threshold=min(2.0, dt - 0.5), drift_threshold=dt)
    if name == "hddm_a":
        return lambda: binary.HDDMA(drift_confidence=cfg.get("drift_confidence", 0.001))
    if name == "hddm_w":
        return lambda: binary.HDDMW(drift_confidence=cfg.get("drift_confidence", 0.001))
    raise KeyError(name)


def _river_columns(factory, Z, n0):
    marks = []
    for j in range(Z.shape[1]):
        d = factory(); col = Z[:, j].tolist()
        for t, v in enumerate(col):
            d.update(v)
            if d.drift_detected and t >= n0:
                marks.append((t, j, None))
    return marks


def _cusum(Z, n0, k, h):
    n, d = Z.shape; sp = np.zeros(d); sn = np.zeros(d); zp = np.zeros(d, int); zn = np.zeros(d, int); marks = []
    for t in range(n):
        z = Z[t]
        sp = np.maximum(0.0, sp + z - k); sn = np.maximum(0.0, sn - z - k)
        zp[sp == 0] = t + 1; zn[sn == 0] = t + 1
        high = (sp > h) | (sn > h)
        if high.any():
            for j in np.flatnonzero(high):
                if t >= n0:
                    marks.append((t, int(j), int(zp[j] if sp[j] > h else zn[j])))
                sp[j] = 0.0; sn[j] = 0.0; zp[j] = t + 1; zn[j] = t + 1
    return marks


def _ewma(Z, n0, lam, L):
    n, d = Z.shape; e = np.zeros(d); lim = L * math.sqrt(lam / (2 - lam)); marks = []
    for t in range(n):
        e = lam * Z[t] + (1 - lam) * e
        high = np.abs(e) > lim
        if high.any():
            for j in np.flatnonzero(high):
                if t >= n0:
                    marks.append((t, int(j), None))
            e[high] = 0.0
    return marks


def stream(name, series, cfg, mode, cache=None):
    """A stream detector in mode "field" (per field; DDM and HDDM on the outside-the-range indicator) or "error" (on the error of
    the model)."""
    n0 = series.warmup
    if mode == "error":
        e = model_error(series, cache)[:, None]
        Z = standardize(e, n0) if name in ("cusum", "ewma") else e
        kind = "REAL"
    else:
        Z = outside_indicator(series.X, n0) if name in ("ddm", "hddm_a", "hddm_w") else standardize(series.X, n0)
        kind = "VIRTUAL"
    if name == "cusum":
        m = _cusum(Z, n0, cfg.get("k", 0.5), cfg.get("h", 5.0))
    elif name == "ewma":
        m = _ewma(Z, n0, cfg.get("lam", 0.2), cfg.get("L", 3.0))
    else:
        m = _river_columns(_factory(name, cfg), Z, n0)
    if mode == "error":
        m = [(t, None, since) for t, _, since in m]
    return merge(m, kind)


# ------------------------------------------------------------------ per-field test (the Evidently and NannyML default)
def per_field_test(series, cfg):
    from scipy.stats import chi2_contingency, ks_2samp
    X = series.X; N, d = X.shape; ref_n = series.warmup
    window, window_step, alpha = cfg.get("window", 1000), cfg.get("window_step", 250), cfg.get("alpha", 0.05)
    ev = []; ref0 = 0; t = ref0 + ref_n + window
    while t <= N:
        R = X[ref0:ref0 + ref_n]; S = X[t - window:t]; accused = []
        for j in range(d):
            if series.numeric:
                p = ks_2samp(R[:, j], S[:, j]).pvalue
            else:
                cats = np.union1d(R[:, j], S[:, j])
                tab = np.array([[np.sum(R[:, j] == c) for c in cats], [np.sum(S[:, j] == c) for c in cats]]); tab = tab[:, tab.sum(0) > 0]
                p = chi2_contingency(tab)[1] if tab.shape[1] > 1 else 1.0
            if p < alpha / d:
                accused.append(j)
        if accused:
            ev.append([t - 1, "VIRTUAL", accused, None]); ref0 = t; t = ref0 + ref_n + window
        else:
            t += window_step
    return ev


# ------------------------------------------------------------------ CJSD (Oda), reimplemented
def _cjsd_block(Xr, yr, Xs, ys, seed, with_y):
    from sklearn.ensemble import RandomForestClassifier
    Xa = np.vstack([Xr, Xs]); Z = np.concatenate([np.zeros(len(Xr)), np.ones(len(Xs))])
    g = np.random.default_rng(seed); fold = g.permutation(len(Z)) % 2
    l1 = np.zeros(len(Z)); l2 = np.zeros(len(Z)); eps = 1e-3
    pairs = [(Xa, l1)]
    if with_y:
        ya = np.concatenate([yr, ys]).astype(float); pairs.append((np.column_stack([Xa, ya]), l2))
    for f in (0, 1):
        tr, te = fold != f, fold == f
        for X_, lo in pairs:
            m = RandomForestClassifier(n_estimators=30, min_samples_leaf=5, random_state=int(seed) + f, n_jobs=1).fit(X_[tr], Z[tr])
            p = np.clip(m.predict_proba(X_[te])[:, 1], eps, 1 - eps)
            lo[te] = -(Z[te] * np.log(p) + (1 - Z[te]) * np.log(1 - p))
    Ix = math.log(2) - float(l1.mean())
    if not with_y:
        return 0.0, 0.0, Ix
    dif = l1 - l2; D = float(dif.mean()); z = D / (dif.std(ddof=1) / math.sqrt(len(dif)) + 1e-12)
    return D, z, Ix


def cjsd(series, cfg, cache=None, log=None):
    """Reference R = the last `win` items of the warm-up; recent window S = the last `win` items; one block every `step` items. REAL if
    z > 3 and D > tau; otherwise VIRTUAL if I_x > tau_x. After a warning, R = the next `win` items. Without a response, only I_x.
    log: when given, receives (t, D, z, I_x) of every block (for the calibration of the default thresholds)."""
    X, y = series.X, series.y; with_y = y is not None; win, step = 1000, 500
    tau, tau_x = cfg.get("tau"), cfg.get("tau_x")
    blocks = cache.setdefault("cjsd", {}) if cache is not None else {}
    yy = y if with_y else np.zeros(series.n)
    ev = []; r0 = max(0, series.warmup - win); t = r0 + win + win        # warm-up shorter than win: the first win items
    while t <= series.n:
        if (r0, t) not in blocks:
            blocks[(r0, t)] = _cjsd_block(X[r0:r0 + win], yy[r0:r0 + win], X[t - win:t], yy[t - win:t], t, with_y)
        D, z, Ix = blocks[(r0, t)]
        if log is not None:
            log.append((t, D, z, Ix))
        kind = None
        if tau is not None:
            if with_y and z > 3.0 and D > tau:
                kind = "REAL"
            elif Ix > tau_x:
                kind = "VIRTUAL"
        if kind:
            ev.append([t - 1, kind, [], None]); r0 = t; t = r0 + win + win
        else:
            t += step
    return ev


# ------------------------------------------------------------------ WATCH and CTM (the original code, adapted)
def _sr(m):
    m = np.asarray(m, float); s = m * np.concatenate([[0.0], np.cumsum(1.0 / m)[:-1]]); s[0] = 0.0
    return s


def _watch_segment(series, s0, weighted, seed, cache):
    """One WATCH segment starting at s0: training [s0, s0 + c/2), calibration [s0 + c/2, s0 + c), test after that. Returns the paths
    of the martingales (of the model and of the input) from item s0 + c on. Cached by (s0, weighted)."""
    key = ("watch", s0, weighted)
    if cache is not None and key in cache:
        return cache[key]
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import NearestNeighbors
    from sklearn.preprocessing import StandardScaler
    from competitors.watch_original import martingales as WM
    from competitors.watch_original.p_values import calculate_p_values
    X, y = series.X, series.y; c = series.warmup; h = c // 2; n_cal = c - h
    tr = slice(s0, s0 + h); Xct = X[s0 + h:]
    np.random.seed(seed)
    nn = NearestNeighbors(n_neighbors=1, algorithm="ball_tree").fit(X[tr])
    vx = nn.kneighbors(Xct)[0].ravel(); px = calculate_p_values(vx)
    with contextlib.redirect_stdout(io.StringIO()):
        _, mx, _, ax = WM.composite_jumper_martingale(px[n_cal:], return_alarm=True)
    mx = np.asarray(mx, float); sx = _sr(mx)
    res = {"mx": mx, "sx": sx, "m": None, "s": None}
    if y is not None:
        asr = np.flatnonzero(sx >= 1000)
        cand = [a for a in (ax, int(asr[0]) if len(asr) else None) if a is not None]
        x_alarm = min(cand) if cand else None
        mod = RandomForestClassifier(n_estimators=100, random_state=seed, n_jobs=1).fit(X[tr], y[tr])
        yct = y[s0 + h:]; pr = mod.predict_proba(Xct); cls = list(mod.classes_)
        v = 1.0 - np.array([pr[i, cls.index(yy)] if yy in cls else 0.0 for i, yy in enumerate(yct)])
        p = calculate_p_values(v)
        if weighted and x_alarm is not None:
            ad = n_cal + x_alarm; sc = StandardScaler().fit(Xct); Xs = sc.transform(Xct); src = Xs[:ad]
            lr = LogisticRegression(warm_start=True, max_iter=200); w_src = None; u = np.random.uniform(size=len(v))
            for k in range(ad, len(v)):
                if w_src is None or (k - ad) % 50 == 0:
                    target = Xs[ad:k + 1] if k + 1 - ad >= 10 else Xs[ad:ad + 10]
                    lr.fit(np.vstack([src, target]), np.concatenate([np.zeros(len(src)), np.ones(len(target))]))
                    pp = np.clip(lr.predict_proba(src)[:, 1], 1e-6, 1 - 1e-6); w_src = pp / (1 - pp)
                pk = float(np.clip(lr.predict_proba(Xs[k:k + 1])[0, 1], 1e-6, 1 - 1e-6)); wk = pk / (1 - pk)
                tot = w_src.sum() + wk
                p[k] = (np.sum(w_src[v[:ad] > v[k]]) + u[k] * (np.sum(w_src[v[:ad] == v[k]]) + wk)) / tot
        with contextlib.redirect_stdout(io.StringIO()):
            _, m, _, _ = WM.composite_jumper_martingale(p[n_cal:], return_alarm=True)
        m = np.asarray(m, float)
        res.update(m=m, s=_sr(m), x_alarm=x_alarm)
    if cache is not None:
        cache[key] = res
    return res


def watch(series, cfg, weighted=True, cache=None):
    """Warning when the martingale reaches cfg['ville'] or its Shiryaev-Roberts statistic reaches cfg['sr'] (defaults of the paper:
    100 and 10^4). With a response: the martingale of the model; REAL if the input martingale did not fire before (at the adaptation
    level of the paper, 100 or SR 1,000), VIRTUAL if it did. Without a response: the input martingale, VIRTUAL. After a warning, it
    starts over with a new warm-up. The random seed is the series seed, or the first 4 bytes of the series name when it has none."""
    ville, srl = cfg.get("ville", 100.0), cfg.get("sr", 1e4); c = series.warmup
    seed = int(series.seed) if series.seed is not None else int.from_bytes(series.name.encode()[:4].ljust(4, b"\0"), "little")
    ev = []; s0 = 0
    while s0 + c < series.n:
        r = _watch_segment(series, s0, weighted, seed, cache)
        m, s = (r["mx"], r["sx"]) if series.y is None else (r["m"], r["s"])
        a1 = np.flatnonzero(m >= ville); a2 = np.flatnonzero(s >= srl)
        cand = [int(a1[0])] if len(a1) else []
        cand += [int(a2[0])] if len(a2) else []
        if not cand:
            break
        a = min(cand); t = s0 + c + a
        if series.y is None:
            kind = "VIRTUAL"
        else:
            kind = "VIRTUAL" if (r.get("x_alarm") is not None and r["x_alarm"] <= a) else "REAL"
        ev.append([int(t), kind, [], None]); s0 = t + 1
    return ev


# ------------------------------------------------------------------ isolation forest
def isolation_forest(series, cfg, cache=None):
    from sklearn.ensemble import IsolationForest
    n0 = series.warmup
    if cache is not None and "isolation_forest" in cache:
        s, offset = cache["isolation_forest"]
    else:
        A = series.X if series.y is None else np.column_stack([series.X, series.y])
        f = IsolationForest(n_estimators=100, contamination="auto", random_state=1, n_jobs=1).fit(A[:n0])
        s, offset = f.score_samples(A), f.offset_
        if cache is not None:
            cache["isolation_forest"] = (s, offset)
    cut = offset if cfg.get("q") is None else float(np.quantile(s[:n0], 1 - cfg["q"]))
    return merge([(int(t), None, None) for t in np.flatnonzero(s[n0:] < cut) + n0], "VIRTUAL")


# ------------------------------------------------------------------ matrix profile (left profile: only the past)
def left_matrix_profile(T, m, cache=None, key=None):
    """The z-normalized distance of each subsequence to its nearest neighbor among the earlier ones (stumpy's left index)."""
    if cache is not None and key in cache:
        return cache[key]
    import stumpy
    from numpy.lib.stride_tricks import sliding_window_view
    T = np.asarray(T, float); P = stumpy.stump(T, m)
    left = P[:, 2].astype(np.int64); W = sliding_window_view(T, m); mu = W.mean(1); sd = W.std(1)
    d = np.full(len(left), np.nan); ok = left >= 0; i = np.flatnonzero(ok); j = left[ok]
    QT = np.einsum("ij,ij->i", W[i], W[j]); flat_i = sd[i] < 1e-7; flat_j = sd[j] < 1e-7
    with np.errstate(divide="ignore", invalid="ignore"):
        r = (QT - m * mu[i] * mu[j]) / (m * sd[i] * sd[j])
    dist = np.sqrt(np.clip(2 * m * (1 - r), 0, None))
    dist = np.where(flat_i & flat_j, 0.0, np.where(flat_i | flat_j, math.sqrt(m), dist))
    d[i] = dist
    if cache is not None:
        cache[key] = d
    return d


def matrix_profile(series, cfg, cache=None):
    m = cfg.get("m", 100); k = cfg.get("k"); n0 = series.warmup; marks = []
    for j in range(series.d):
        d = left_matrix_profile(series.X[:, j], m, cache, ("matrix_profile", j, m))
        end = np.arange(len(d)) + m - 1                     # the item at which the subsequence is complete
        warm = d[(end < n0) & np.isfinite(d)]
        if len(warm) == 0:
            continue
        cut = float(warm.max()) if k is None else float(warm.mean() + k * warm.std())
        for i in np.flatnonzero((end >= n0) & np.isfinite(d) & (d > cut)):
            marks.append((int(end[i]), j, int(i)))
    return merge(marks, "VIRTUAL")


# ------------------------------------------------------------------ HTM (the htmcore detector of the NAB community)
def htm(series, cfg, fields=None, cache=None):
    from competitors.htm_nab import scores
    threshold = cfg.get("threshold", 0.5014187204194446); n0 = series.warmup; marks = []
    for j in (range(series.d) if fields is None else fields):
        key = ("htm", j)
        if cache is not None and key in cache:
            s = cache[key]
        else:
            s = np.asarray(scores(series.X[:, j], series.extra.get("timestamps"), {"seed": 1}))
            if cache is not None:
                cache[key] = s
        for t in np.flatnonzero(s[n0:] >= threshold) + n0:
            marks.append((int(t), j, None))
    return merge(marks, "VIRTUAL")


# ------------------------------------------------------------------ the detector
def detector(series, cfg):
    """The detector: the monitor with the warm-up, the live record and the trajectories. Without a response, y = 0 at every item,
    the scale ladder for a field that starts flat and the declared minimum unit. Returns the phase 0 warnings, the phase 500 reports
    and the trajectory events. cfg {"own_warmup": True} uses the warm-up of the series instead of 2,000 items."""
    from detector import Monitor, declared_scale
    W0 = series.warmup if cfg.get("own_warmup") else 2000
    W = None if W0 == 2000 else W0
    if series.y is not None:
        mon = Monitor("s", series.d, series.K, W0=W0, W=W, H=5000, numeric=series.numeric)
        ys = series.y
    else:
        res = series.resolution or [1.0] * series.d
        mon = Monitor("s", series.d, 2, W0=W0, W=W, H=5000, scale=declared_scale(res), sd_min=res, scale_only_if_flat=True)
        ys = np.zeros(series.n, int)
    warnings, reports, events = [], [], []
    for t in range(series.n):
        if series.n <= W0:
            break
        for r in mon.item(series.X[t], int(ys[t])):
            if r.get("kind") == "EVENT":
                events.append({k: v for k, v in r.items() if k not in ("part", "curve")})
            elif r.get("phase") == 0:
                warnings.append([int(r["t"]), r["kind"], sorted(int(c["index"]) for c in r["fields"]), r.get("since")])
            elif r.get("phase") == 500:
                reports.append({"t": int(r["updates"]),
                                "fields": [dict({"field": int(c["index"])}, **{k: v for k, v in c.items() if k not in ("field", "index")})
                                           for c in r["fields"]]})
    return warnings, reports, events


# ------------------------------------------------------------------ the list
PER_FIELD = ["page_hinkley", "cusum", "ewma", "adwin", "kswin", "ddm", "hddm_a", "hddm_w"]


def methods_for_series(series):
    """The methods that run on this series, with the mode of each stream detector."""
    ms = ["detector"] + [f"{m}/field" for m in PER_FIELD]
    if series.y is not None:
        ms += [f"{m}/error" for m in PER_FIELD]
    ms += ["per_field_test", "cjsd", "watch"] + (["ctm"] if series.y is not None else []) + ["isolation_forest", "matrix_profile", "htm"]
    return ms


def run(method, series, cfg, cache=None, htm_fields=None):
    if method == "detector":
        return detector(series, cfg)
    name, _, mode = method.partition("/")
    if name in PER_FIELD:
        return stream(name, series, cfg, mode, cache)
    if name == "per_field_test":
        return per_field_test(series, cfg)
    if name == "cjsd":
        return cjsd(series, cfg, cache)
    if name in ("watch", "ctm"):
        return watch(series, cfg, weighted=(name == "watch"), cache=cache)
    if name == "isolation_forest":
        return isolation_forest(series, cfg, cache)
    if name == "matrix_profile":
        return matrix_profile(series, cfg, cache)
    if name == "htm":
        return htm(series, cfg, htm_fields, cache)
    raise KeyError(method)
