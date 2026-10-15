"""The names of the approval run, where a name feeds a hash whose order matters.
Two names are hashed and the hash decides an order that reaches the results, so both are computed with the names that the approval run
used (protocol/publication/keymap.json, old name -> new name):
- the output file of a series (runner.run.output_file_name): the metrics read the outputs in file-name order, and the company rows
  resample the lives in the order in which they first appear;
- the NAB detector name of a method and configuration (metrics.nab_score.detector_name): NAB sums the per-file scores in the order
  in which its directory listing returns the result files, whose names start with the detector name, and the last digits of the
  scores depend on that order."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KM = None


def _keymap():
    global _KM
    if _KM is None:
        km = json.load(open(os.path.join(ROOT, "protocol", "publication", "keymap.json"), encoding="utf-8"))
        rev = {k: {new: old for old, new in km[k].items()} for k in ("base", "variant", "synthetic_type", "method", "config_label")}
        rev["config_parameter"] = {}
        for old_method, params in km["config_parameter"].items():
            rev["config_parameter"][km["method"][old_method]] = {new: old for old, new in params.items()}
        _KM = rev
    return _KM


def series_key(base, name, variant, seed):
    """"base|name|variant|seed" with the names of the approval run."""
    L = _keymap()
    if base == "synthetic":
        name = L["synthetic_type"].get(name, name)
    return f"{L['base'].get(base, base)}|{name}|{L['variant'].get(variant, variant)}|{seed}"


def method_config(method, cfg):
    """"method|configuration key" with the names of the approval run (the configuration rendered in its sorted form)."""
    L = _keymap()
    old_method = L["method"].get(method, method)
    if cfg in L["config_label"]:
        old_cfg = L["config_label"][cfg]
    else:
        names = L["config_parameter"].get(method.split("/")[0], {})
        old_cfg = ",".join(f"{k}={v}" for k, v in sorted((names.get(k, k), v) for k, v in (p.split("=", 1) for p in cfg.split(","))))
    return f"{old_method}|{old_cfg}"
