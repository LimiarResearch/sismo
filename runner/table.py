"""The table of the benchmark, generated only from the outputs: the rows (metrics/rows.py) and the NAB score (metrics/nab_score.py).
python -m runner.table <rows.json> [<nab.json>]  -> the table in Markdown on standard output."""
import argparse
import json

from metrics.rows import benchmark_verdict

NAB_GROUPS = {"part_series": "Approval series, default and tuned configurations", "all_58_default": "All 58 series, default configurations"}
HTM_PUBLISHED = ("Published, not measured here: HTM (the htmcore detector of the NAB community) scores 63.08 on the whole corpus "
                 "(htm-community/NAB, results/final_results.json, commit 98cdba6). That number is from 2019 and 2020, from an earlier "
                 "version of the htm.core likelihood, with the threshold optimized by NAB on the whole corpus; the current htmcore code, "
                 "which this benchmark runs, was changed in 2021 with no new published score (see the record of the approval).")


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.3f}"
    if isinstance(v, dict):
        return "; ".join(f"{k} {fmt(x)}" for k, x in v.items())
    return str(v)


def detector_cell(L):
    det = L.get("detector")
    if "n" in L and (isinstance(det, float) or det is None):
        if "n_null" in L:
            return f"{fmt(det)} (n = {L['n']}; null {fmt(L.get('null'))}, n = {L.get('n_null')})"
        return f"{fmt(det)} (n = {L['n']})"
    return fmt(det)


def main():
    ap = argparse.ArgumentParser(description="The table of the benchmark in Markdown.")
    ap.add_argument("rows"); ap.add_argument("nab", nargs="?")
    a = ap.parse_args()
    rows = json.load(open(a.rows, encoding="utf-8"))
    print("| row | detector | best competitor | its value | standard error of the difference | verdict | status |")
    print("|---|---|---|---|---|---|---|")
    for L in rows:
        print(f"| {L['row']} | {detector_cell(L)} | {fmt(L.get('best_competitor'))} | {fmt(L.get('best_value'))} | {fmt(L.get('se_difference'))} | "
              f"{L.get('verdict', '-')} | {L['status']} |")
    vb = benchmark_verdict(rows)
    print(f"\n**The benchmark: {vb['status']}** ({vb['rows_that_decide']} rows decide; not passed: {', '.join(vb['not_passed']) or 'none'})")
    if a.nab:
        nab = json.load(open(a.nab, encoding="utf-8"))
        print("\n**NAB score (standard profile; official NAB rules; information only)**")
        for group, title in NAB_GROUPS.items():
            if group not in nab:
                continue
            print(f"\n{title} ({nab[group]['series']} series)\n\n| method and configuration | score |\n|---|---|")
            for k, v in sorted(nab[group]["scores"].items(), key=lambda kv: -kv[1]):
                print(f"| {k} | {v:.2f} |")
        print(f"\n{HTM_PUBLISHED}")


if __name__ == "__main__":
    main()
