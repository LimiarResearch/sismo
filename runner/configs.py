"""The configurations of the methods: the default (the one of the library or of the paper) and the grid of the development search
(protocol, section 4.3). The detector has a single configuration, "default". The tuned configuration of each competitor comes from the
development search and is kept in protocol/tuned.json, frozen before the approval run. The default CJSD thresholds come from the
calibration on the development nulls (up to zero observed warnings) and are kept in protocol/cjsd_default.json."""
import itertools

DEFAULT = {
    "detector": {},
    "page_hinkley": {"min_instances": 30, "delta": 0.005, "threshold": 50.0},
    "cusum": {"k": 0.5, "h": 5.0},
    "ewma": {"lam": 0.2, "L": 3.0},
    "adwin": {"delta": 0.002},
    "kswin": {"alpha": 0.005, "window_size": 100, "stat_size": 30},
    "ddm": {"warm_start": 30, "drift_threshold": 3.0},
    "hddm_a": {"drift_confidence": 0.001},
    "hddm_w": {"drift_confidence": 0.001},
    "per_field_test": {"alpha": 0.05, "window": 1000, "window_step": 250},
    "cjsd": {"q_tau": 1.0, "q_tau_x": 1.0},
    "watch": {"ville": 100.0, "sr": 1e4},
    "ctm": {"ville": 100.0, "sr": 1e4},
    "isolation_forest": {"q": None},
    "matrix_profile": {"m": 100, "k": None},
    "htm": {"threshold": 0.5014187204194446},
}


def _prod(**axes):
    ch = list(axes)
    return [dict(zip(ch, v)) for v in itertools.product(*(axes[c] for c in ch))]


GRID = {
    "page_hinkley": _prod(min_instances=[30], threshold=[5.0, 10.0, 20.0, 50.0, 100.0, 200.0], delta=[0.0005, 0.005, 0.05]),
    "cusum": _prod(k=[0.25, 0.5, 1.0], h=[3.0, 4.0, 5.0, 8.0, 12.0]),
    "ewma": _prod(lam=[0.05, 0.1, 0.2, 0.3], L=[2.5, 3.0, 3.5, 4.0]),
    "adwin": _prod(delta=[1e-6, 1e-5, 1e-4, 0.002, 0.01, 0.05]),
    "kswin": _prod(alpha=[1e-5, 1e-4, 0.005], window_size=[100, 300], stat_size=[30]),
    "ddm": _prod(drift_threshold=[2.0, 3.0, 4.0, 5.0], warm_start=[30, 100]),
    "hddm_a": _prod(drift_confidence=[1e-5, 1e-4, 1e-3, 1e-2]),
    "hddm_w": _prod(drift_confidence=[1e-5, 1e-4, 1e-3, 1e-2]),
    "per_field_test": _prod(alpha=[0.001, 0.01, 0.05], window=[250, 500, 1000], window_step=[50, 250]),
    "cjsd": _prod(q_tau=[0.9, 0.99, 1.0], q_tau_x=[0.9, 0.99, 1.0]),
    "watch": _prod(ville=[20.0, 100.0, 1000.0], sr=[1e2, 1e3, 1e4, 1e5, 1e6]),
    "ctm": _prod(ville=[20.0, 100.0, 1000.0], sr=[1e2, 1e3, 1e4, 1e5, 1e6]),
    "isolation_forest": _prod(q=[None, 0.99, 0.995, 0.999, 0.9999]),
    "matrix_profile": _prod(m=[100, 256], k=[None, 3.0, 4.0, 5.0, 6.0]),
    "htm": _prod(threshold=[0.5014187204194446, 0.5, 0.9, 0.99, 0.999, 0.9999]),
}

# HTM costs about 6.6 s per 1,000 points per field (measured); it runs where the series is univariate (NAB) and on the telemetry
# field of SMAP and MSL (field 0; the others are 0/1 commands). On the other bases it is not run, because of the cost (synthetic
# streams: 20 fields x 20,000 items x 1,020 runs; SMD: 38 fields x 50,000 items x 28 machines; company: 495 fields x 43,200 minutes
# per life).
HTM_FIELDS = {"nab": None, "smap": [0], "msl": [0]}

# The fixed order of the methods (with their modes). When competitors tie on the main metric of a row, the one that comes later in
# this order is the best competitor of the row (metrics/rows.py); configurations of the same method are ordered by their key.
METHOD_ORDER = ["adwin/field", "adwin/error", "cjsd", "ctm", "cusum/field", "cusum/error", "ddm/field", "ddm/error", "detector",
                "ewma/field", "ewma/error", "isolation_forest", "hddm_a/field", "hddm_a/error", "hddm_w/field", "hddm_w/error", "htm",
                "kswin/field", "kswin/error", "page_hinkley/field", "page_hinkley/error", "matrix_profile", "per_field_test", "watch"]


def config_key(cfg):
    """The key of a configuration in the outputs: "name=value" pairs sorted by name and joined by commas; "default" when empty."""
    return ",".join(f"{k}={cfg[k]}" for k in sorted(cfg)) or "default"


def base_method(method):
    return method.split("/")[0]


def method_rank(method_cfg):
    """Sort key of a (method, configuration key) pair: the position of the method in METHOD_ORDER, then the configuration key."""
    m, c = method_cfg
    return (METHOD_ORDER.index(m) if m in METHOD_ORDER else len(METHOD_ORDER), m, c)
