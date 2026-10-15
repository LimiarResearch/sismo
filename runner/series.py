"""The series of the benchmark: each base becomes a list of series with fields, response (when there is one), warm-up, scored stretch,
truth events with their tolerance window, true fields and clock. No method is called here.

Rules declared in the protocol (sections 3 and 5):
- development and approval: a public series belongs to development when int(sha256(name)[:8], 16) % 3 == 0;
- warm-up: the first items that every method uses to learn (2,000 in the rows that decide);
- tolerance window of an event: NAB, the official window; SMD, SMAP and MSL, [start, end + max(10, duration)); synthetic streams,
  4,000 items for input changes, for gradual relation changes and for sea, 2,000 items for the other relation changes; simulated
  company, see runner/company.py;
- an event whose window ends before the scored stretch is out of reach of every method: it does not count and is counted apart."""
import ast
import csv
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
T_SYNTH, N_SYNTH = 10000, 20000


@dataclass
class Event:
    start: int                       # the true start (item index)
    end: int                         # the true end (exclusive)
    window: tuple                    # [a, b): where a warning counts as a detection
    fields: frozenset = None         # the true fields (None: the base does not mark them)
    kind: str = "VIRTUAL"            # VIRTUAL (log, the input changed) or REAL (alert, the relation broke)
    mark: int = None                 # the item marked by the base for the latency (NAB: the labeled point); None = start
    extra: dict = field(default_factory=dict)


@dataclass
class Series:
    base: str
    name: str
    part: str                        # "development" or "approval"
    X: np.ndarray
    y: np.ndarray = None             # the response (None: no response; the detector then receives y = 0)
    numeric: bool = True
    K: int = 2
    warmup: int = 2000
    score_start: int = 2000
    events: list = field(default_factory=list)
    out_of_reach: int = 0            # events that end before the scored stretch
    minutes_per_item: float = None   # clock, when the base has one
    field_names: list = None
    resolution: list = None          # the minimum unit of each field, for the monitor (field that starts flat, smallest deviation)
    variant: str = "main"            # main | shuffled | official (NAB) | warmup500 (NAB)
    ignore: list = field(default_factory=list)    # stretches [a, b) where warnings of a kind do not count as false: (a, b, kind)
    seed: int = None
    extra: dict = field(default_factory=dict)

    @property
    def n(self):
        return len(self.X)

    @property
    def d(self):
        return self.X.shape[1]


def part_of(name):
    return "development" if int(hashlib.sha256(name.encode()).hexdigest()[:8], 16) % 3 == 0 else "approval"


def public_resolution(X0):
    """The minimum unit declared by the loader of the public bases: the smallest positive difference between distinct values of the
    field in the warm-up; 1.0 if the field is constant in the warm-up."""
    res = []
    for j in range(X0.shape[1]):
        u = np.unique(X0[:, j]); dif = np.diff(u)
        res.append(float(dif[dif > 0].min()) if (dif > 0).any() else 1.0)
    return res


def shuffle(s, seed):
    """The same series with the order of the items drawn at random: removes every change over time and keeps the marginals. Every
    warning after the warm-up is false."""
    g = np.random.default_rng(seed); p = g.permutation(s.n)
    return Series(base=s.base, name=s.name, part=s.part, X=s.X[p], y=None if s.y is None else s.y[p], numeric=s.numeric, K=s.K,
                  warmup=s.warmup, score_start=s.warmup, events=[], out_of_reach=0, minutes_per_item=s.minutes_per_item,
                  field_names=s.field_names, resolution=None if s.resolution is None else s.resolution, variant="shuffled", seed=s.seed,
                  extra={"permutation_seed": seed, **({"timestamps": s.extra["timestamps"]} if "timestamps" in s.extra else {})})


def _clip_events(events, score_start):
    """Drops the events whose window ends before the scored stretch and cuts the start of the windows that cross into it."""
    inside, outside = [], 0
    for e in events:
        a, b = e.window
        if b <= score_start:
            outside += 1; continue
        e.window = (max(a, score_start), b); inside.append(e)
    return inside, outside


# ------------------------------------------------------------------ synthetic
def synthetic(seeds, part, shuffled=True):
    sys.path.insert(0, ROOT)
    from generators import synthetic as G
    out = []
    for name in G.ALL:
        for s in seeds:
            X, y, exp, truth, num, K = G.stream(name, s)
            ev = []
            if exp is not None:
                win = (4000 if ("gradual" in name or name == "sea") else 2000) if exp == "REAL" else 4000
                end = T_SYNTH + 2000 if ("gradual" in name or name == "ramp_all") else T_SYNTH + 1
                ev = [Event(T_SYNTH, end, (T_SYNTH, T_SYNTH + win), frozenset(int(v) for v in truth) or None, exp)]
            ig = []
            if name in ("slow_abrupt", "slow_real"):
                ig = [(2000, T_SYNTH, "VIRTUAL")]         # before T the slow drift is already an input change; its logs are not false
            if name in ("slow_all", "slow_few"):
                ig = [(2000, N_SYNTH, "VIRTUAL")]         # the whole slow drift: its log is what A5 asks for
            ser = Series(base="synthetic", name=name, part=part, X=np.asarray(X, float), y=np.asarray(y, int), numeric=bool(num), K=int(K),
                         warmup=2000, score_start=2000, events=ev, field_names=[f"x{j}" for j in range(X.shape[1])], ignore=ig, seed=s,
                         extra={"expected": exp, "truth": sorted(int(v) for v in truth)})
            out.append(ser)
            if shuffled and exp is not None:
                out.append(shuffle(ser, 7_000_000 + s))
    return out


# ------------------------------------------------------------------ NAB
def _timestamps(path):
    ts, vs = [], []
    with open(path, encoding="utf-8") as f:
        r = csv.reader(f); next(r)
        for row in r:
            ts.append(datetime.fromisoformat(row[0])); vs.append(float(row[1]))
    return ts, np.array(vs, float)


def _index(ts, s, side):
    s = datetime.fromisoformat(s.split(".")[0])
    import bisect
    return bisect.bisect_left(ts, s) if side == "start" else bisect.bisect_right(ts, s)


def nab(raw, variant="main"):
    """variant: main (warm-up of 2,000 for everyone), official (the NAB rules: warm-up = probationary period, 15% of the series and at
    most 750 items; information only), warmup500 (warm-up of 500 items for everyone; information only)."""
    root = os.path.join(raw, "nab")
    windows = json.load(open(os.path.join(root, "labels/combined_windows.json"))); labels = json.load(open(os.path.join(root, "labels/combined_labels.json")))
    out = []
    for name in sorted(windows):
        ts, v = _timestamps(os.path.join(root, "data", name)); n = len(v)
        warm = {"main": 2000, "official": int(min(math.floor(0.15 * n), 0.15 * 5000)), "warmup500": 500}[variant]   # official: nab/util.py getProbationPeriod
        evs = []
        for (a, b), m in zip(windows[name], labels[name]):
            ia, ib, im = _index(ts, a, "start"), _index(ts, b, "end"), _index(ts, m, "start")
            evs.append(Event(ia, ib, (ia, ib), None, "VIRTUAL", mark=im))
        inside, outside = _clip_events(evs, warm)
        step = float(np.median(np.diff([t.timestamp() for t in ts]))) / 60.0
        X = v[:, None]
        out.append(Series(base="nab", name=name, part=part_of(name), X=X, warmup=min(warm, n), score_start=min(warm, n), events=inside,
                          out_of_reach=outside, minutes_per_item=step, field_names=["value"], resolution=public_resolution(X[:min(warm, n)]),
                          variant=variant, extra={"n_windows": len(windows[name]), "too_short": n <= warm, "timestamps": ts}))
    return out


# ------------------------------------------------------------------ SMD
def smd(raw):
    root = os.path.join(raw, "smd", "ServerMachineDataset"); out = []
    for fname in sorted(os.listdir(os.path.join(root, "test"))):
        tr = np.loadtxt(os.path.join(root, "train", fname), delimiter=","); te = np.loadtxt(os.path.join(root, "test", fname), delimiter=",")
        lab = np.loadtxt(os.path.join(root, "test_label", fname)); n0 = len(tr)
        interp = {}
        for row in open(os.path.join(root, "interpretation_label", fname)):
            seg, dims = row.strip().split(":"); a, b = (int(x) for x in seg.split("-"))
            interp[(a, b)] = frozenset(int(d) - 1 for d in dims.split(","))
        d_ = np.diff(np.concatenate([[0], lab, [0]])); starts = np.flatnonzero(d_ == 1); ends = np.flatnonzero(d_ == -1)
        evs = []
        for a, b in zip(starts.tolist(), ends.tolist()):
            dur = b - a
            fields = next((c for (ia, ib), c in interp.items() if ia <= a <= ib or a <= ia < b), None)
            evs.append(Event(n0 + a, n0 + b, (n0 + a, n0 + b + max(10, dur)), fields, "VIRTUAL", extra={"duration": int(dur)}))
        X = np.vstack([tr, te]); ss = max(n0, 2000)
        inside, outside = _clip_events(evs, ss)
        out.append(Series(base="smd", name=fname, part=part_of(fname), X=X, warmup=2000, score_start=ss, events=inside, out_of_reach=outside,
                          minutes_per_item=1.0, field_names=[f"dim{j + 1}" for j in range(X.shape[1])], resolution=public_resolution(X[:2000]),
                          extra={"train": n0, "train_null": (2000, n0)}))
    return out


# ------------------------------------------------------------------ SMAP and MSL
def smap_msl(raw, craft):
    root = os.path.join(raw, "smap_msl", "data", "SMAP_MSL"); out = []
    for r in csv.DictReader(open(os.path.join(root, "labeled_anomalies.csv"))):
        if r["spacecraft"] != craft:
            continue
        c = r["chan_id"]; tr = np.load(os.path.join(root, "train", c + ".npy")); te = np.load(os.path.join(root, "test", c + ".npy"))
        n0 = len(tr); seqs = ast.literal_eval(r["anomaly_sequences"]); classes = [c.strip(" '\"") for c in r["class"].strip("[]").split(",")]
        evs = []
        for i, (a, b) in enumerate(seqs):
            dur = b + 1 - a
            evs.append(Event(n0 + a, n0 + b + 1, (n0 + a, n0 + b + 1 + max(10, dur)), None, "VIRTUAL",
                             extra={"duration": int(dur), "class": classes[i] if i < len(classes) else None}))
        X = np.vstack([tr, te]).astype(float); ss = max(n0, 2000)
        inside, outside = _clip_events(evs, ss)
        out.append(Series(base=craft.lower(), name=c, part=part_of(c), X=X, warmup=2000, score_start=ss, events=inside, out_of_reach=outside,
                          field_names=[f"c{j}" for j in range(X.shape[1])], resolution=public_resolution(X[:2000]), extra={"train": n0, "train_null": (2000, n0)}))
    return out
