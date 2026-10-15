# Sismo: a public benchmark

A reproducible benchmark that measures what Sismo (in the code and below, "the detector") does and compares it, on the same series and
under the same rules, with 15 known methods. The protocol was written and frozen (sha256) before any run; the approval seeds were drawn
from the hash of the frozen files; the approval ran once. Every row is in the table, passed or not.

## What the detector claims

For a set of fields observed over time, it answers:
- **where**: which field left its normal, among N fields;
- **when**: the instant the change started (not only when it became obvious);
- **what**: up or down, how much in standard deviations of the field's own normal, and the trajectory (stopped growing, came back,
  was replaced, became the new normal).

When a model's response is available, it separates an **alert** (the relation between fields and response broke: retrain) from a
**log** entry (the input changed: the model still holds). It **keeps slow drift** in the log, instead of discarding it or alerting.

## Declared limits (measured in the table, outside the verdict)

- **L1**: a relation that breaks in the middle of a slow drift of the same part.
- **L2**: a change only in the combination of categories.
- **L3**: XOR (the change is only in the mechanism; the margins do not change).
- **L4**: an isolated spike of one to a few items (the spike falls in the top quantile bin, which already receives 12.5% of normal
  items). Every public base reports its L4 row (P1L4, P4L4, P5L4, P6L4), with n = 0 when the base has no event shorter than 10 items.
- **The warm-up**: the detector learns from the first 2,000 items and does not warn before item 2,176. In the rows that decide, every
  method uses the same warm-up; the row "P1c NAB (warmup500, information only): event F1" shows its price, with a warm-up of 500 for
  every method. Series shorter than the warm-up (9 NAB series) are out of reach. UCR and Yahoo S5 are not part of this benchmark.

## The table

Every row of the benchmark, the passed and the failed ones. The value of the best competitor is that of the best method allowed in
the row (a method whose false warnings on series with no change go over the ceiling is not allowed, Sismo included); each row is
decided at two standard errors.

| Row | Sismo | Best allowed competitor | Its value | Verdict | Status |
|---|---|---|---|---|---|
| S1 relation breaks: alert | 0.996 | CJSD | 0.701 | won | passed |
| S2 input changes: log | 0.929 | CJSD | 0.879 | won | passed |
| S3 where: detection with the right field, among N | 0.996 | ADWIN (per field) | 0.438 | won | passed |
| S4a what: right direction | 1.000 (null 0.500) | none | - | above null | passed |
| S4b what: size within 0.25 sd | 1.000 (null 0.240) | none | - | above null | passed |
| S4c what: became the new normal on the steps that stay | 0.978 (null 0.000) | none | - | above null | passed |
| S5 slow drift: in the log and no alert | 1.000 | Per-field test | 1.000 | tied | passed |
| S6 declared limit L1: slow_real | 0.929 | CJSD | 0.333 | won | limit L1 not confirmed in this sample |
| S6 declared limit L2: cat_real | 0.520 | CJSD | 0.114 | won | limit L2 not confirmed in this sample |
| S6 declared limit L3: xor | 0.000 | CJSD | 0.967 | lost | limit L3 confirmed |
| S7 nulls: runs with a warning (ceiling: alert 2%, log 5%) | alert 0/370, log 6/370 | none | - | - | passed |
| P1 NAB: event F1 | 0.165 | HDDM_W (per field) | 0.405 | lost | failed |
| P1L4 NAB: events shorter than 10 items (limit L4) | no event (n = 0) | none | - | no data | limit L4 not measured (n = 0) |
| P1c NAB (warmup500, information only): event F1 | 0.213 | HDDM_A (per field) | 0.351 | lost | information only |
| P4 SMD: event F1 | 0.063 | CJSD | 0.000 | won | failed (Sismo's null above the ceiling) |
| P4L4 SMD: events shorter than 10 items (limit L4) | 0.071 | CJSD | 0.000 | won | limit L4 not confirmed in this sample |
| P4o SMD where: detection with the right fields, among 38 | 0.180 | none | - | no competitor | failed (Sismo's null above the ceiling) |
| P5 SMAP: event F1 | 0.091 | Per-field test | 0.368 | lost | failed (Sismo's null above the ceiling) |
| P5L4 SMAP: events shorter than 10 items (limit L4) | no event (n = 0) | none | - | no data | limit L4 not measured (n = 0) |
| P6 MSL: event F1 | 0.222 | Per-field test | 0.176 | tied | failed (Sismo's null above the ceiling) |
| P6L4 MSL: events shorter than 10 items (limit L4) | no event (n = 0) | none | - | no data | limit L4 not measured (n = 0) |
| M1 contingency: warning on the route's error field within 60 min | 0.700 | Matrix profile | 1.000 | lost | failed |
| M2 incident: warning on the probe within 10 min and start attributed inside the window | 1.000 | HDDM_W (per field) | 1.000 | tied | passed |
| M3 regime change: became the new normal within 15 days | 0.667 (null 0.000) | none | - | above null | passed |
| M4 drift: the portfolio becomes the new normal in the normal lives and never without drift | normal lives [2, 0, 1], no-drift life [1] | none | - | - | failed |
| M5 return: back to normal within 180 min after the outage | 0.000 (null 0.000) | none | - | not above null | failed |

**The benchmark: FAILED.** 18 rows decide; 10 passed (S1, S2, S3, S4a, S4b, S4c, S5, S7, M2, M3) and 8 did not (P1, P4, P4o, P5, P6,
M1, M4, M5). The declared limits and the information rows do not decide.

NAB score (standard profile, official NAB rules, information only): Sismo scores 14.27 on the 36 approval series (best: HTM, 54.92)
and 16.27 on all 58 series with default configurations (best: DDM, 35.00).

The full table, generated by runner/table.py, is results/publication/table.txt (plain text, because the method configurations contain the character "|"): it adds the configuration of each best competitor, the
standard error of each difference and the NAB score of every method and configuration. The reproduction command checks that the table
it computes is equal to that file, number by number.

The criteria of each row, the nulls and the ceilings are in protocol/PROTOCOL.md (section 6). The record of the approval run is in
protocol/approval_record.md. The hashes of the frozen files are in protocol/frozen_publication.sha256 (publication code) and
protocol/history/frozen_approval_original.sha256 (approval code); the seeds are in protocol/seeds.json.

In results/publication/table.txt, method names are the identifiers in the code. The 15 competitor methods: page_hinkley, cusum, ewma, adwin, kswin, ddm,
hddm_a, hddm_w (river, or exact replicas of it), per_field_test (a per-field two-sample test, KS for numbers and chi-square for
categories, Bonferroni), cjsd, watch and ctm (WATCH and CTM, its unweighted variant, the baseline of the WATCH paper; CTM runs only
where there is a response), isolation_forest, matrix_profile and htm (HTM, the htmcore detector of the NAB community). The suffix
/field means the method watches each field (a warning names the field); /error means it watches the error of an online model of the
response. The text after "|" is the configuration; "detector|default" is the detector with its single configuration.

## How to reproduce

Linux, Python 3.11, cmake, g++, git, curl, unzip, uv. One command:

```
./reproduce.sh [work_folder]
```

It creates the two environments with pinned versions (requirements.txt and requirements-nab.txt), builds htm.core
(data/build_htm.sh), downloads the public data from pinned origins and checks the sha256 of every file (data/download.py,
data/sources.json), checks the files against protocol/frozen_publication.sha256, generates the lives of the simulated company, runs the
approval (runner/batch.sh, outputs in outputs/reproduction/), computes the rows (metrics/rows.py) and the NAB score
(metrics/nab_score.py), and checks the warning list of every series against protocol/publication_warnings.sha256 and the table against
the one in this file. Any failed check stops the script with a message. A run that stops can be resumed with the same command: series
whose output is already written are skipped. Cost: the approval took about 14.5 hours on a machine with 4 cores and 15 GB of memory.

The outputs of every series of both runs are published at https://huggingface.co/datasets/LimiarResearch/sismo-benchmark-runs: approval_original.zip (the approval run, with its rows, NAB
score, table and run log), publication.zip (the publication run) and lives.zip (the six simulated company lives both runs used). The
approval outputs are written with the names of the approval run; without running any method, they can be converted to the current
schema and the table computed from them:

```
python protocol/publication/compare_runs.py --convert approval_original outputs/approval
python -m metrics.rows outputs/approval --lives lives --json rows.json
python -m metrics.nab_score outputs/approval/nab/official <nab_python> data/raw nab_work --json nab.json
python -m runner.table rows.json nab.json
```

The NAB score needs the NAB environment (requirements-nab.txt) and the NAB code downloaded by data/download.py.

## Publication version and proof

The approval ran on code written in Portuguese. For publication, the code and documentation were translated to English and cleaned,
with no change meant to any computation; the publication code was frozen, the whole approval was run again with it and the same seeds,
and every series was compared with the original outputs: all 2,047 series are identical, and the rows, the NAB score and the table
computed from the publication run are identical to those of the approval run (results/publication/comparison.txt). What changed, the defects fixed and the result of that comparison are in
protocol/approval_record.md (section "Publication version"); the tools and the map from old to new names are in protocol/publication/
(see protocol/publication/README.md).

## How to add a competitor

1. Write the method in competitors/methods.py with the interface run(method, series, cfg, cache) -> list of warnings [t, kind, fields,
   since], and add it to methods_for_series (or to PER_FIELD, for a stream detector that runs per field and on the error).
2. Declare its default configuration and its grid in runner/configs.py (DEFAULT, GRID) and give it a place in METHOD_ORDER.
3. Write a new version of the protocol (protocol/PROTOCOL.md), freeze (python -m runner.freeze), run the development round
   (sh runner/batch.sh <python> <run> development data/raw), choose the tuned configuration (python -m runner.tune), freeze again,
   draw the seeds (python -m runner.seeds) and run the approval once (sh runner/batch.sh <python> <run> approval data/raw). Nothing
   changes in the detector or in the other competitors.

## Data and licenses

- The public data are not redistributed: NAB (numenta/NAB), SMD (NetManAIOps/OmniAnomaly), SMAP and MSL (the telemanom data, through
  the imperial-qore/TranAD mirror, with the labels checked against the original), each under its own license.
- The simulated company (generators/company/) writes its process names, field names, team names and ground truth in Portuguese; they
  are data and are kept as written. The glossary is in generators/company/README.md.
- The detector (detector/): AGPL-3.0 (LICENSE).
- Runners, metrics and generators: Apache-2.0 (LICENSE-APACHE).
- Copied third-party code: competitors/watch_original (BSD-3-Clause, aaronhan223/watch); competitors/htm_nab.py (a port of the
  htmcore detector of the NAB community, AGPL-3.0). Details in NOTICE.
