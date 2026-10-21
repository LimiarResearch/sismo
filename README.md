# Sismo: a public benchmark

A reproducible benchmark that measures what Sismo (in the code and below, "the detector") does and compares it, on the same series and
under the same rules, with 15 known methods. A development run came first (protocol v1); the approval protocol (v2) was written and
frozen (sha256) after it and before the approval run; the approval seeds were drawn from the hash of the frozen approval files. The
approval run stopped twice and was resumed, and it was later run again in full with the publication code, with identical results (see
"Publication version and proof"). Every row is in the table, passed or not.

Seven independent reviews examined this material after the approval run. Their reports, the list of every point they raised and the
status of each (paineis/RESSALVAS.md), and the summary screens are in paineis/ (in Portuguese); the points that concern how to read
the table are in "Known limitations and caveats" below. Nothing frozen was changed because of them: the fixes that need a new run are
left for a version 2 of the protocol.

## What the detector claims

For a set of fields observed over time, it answers:
- **where**: which field left its normal, among N fields;
- **when**: the instant the change started (not only when it became obvious);
- **what**: up or down, how much in standard deviations of the field's own normal, and the trajectory (stopped growing, came back,
  was replaced, became the new normal).

When a model's response is available, it separates an **alert** (the relation between fields and response broke: retrain) from a
**log** entry (the input changed: the model still holds). It **keeps slow drift** in the log, instead of discarding it or alerting.

## Which detector this measures

The table holds for the detector code in detector/, as published in this repository and frozen by its sha256 in
protocol/frozen_publication.sha256, run with its single configuration. Any other version of the detector, or this code with other
options, is not covered by this table: it has to be run again under the same protocol before any number here is used for it.

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
categories, Bonferroni), cjsd (the Conditional Jensen-Shannon Discrepancy of Oda, arXiv 2608.19885, on sliding windows, as the protocol
describes), watch and ctm (WATCH and CTM, its unweighted variant, the baseline of the WATCH paper; CTM runs only
where there is a response), isolation_forest, matrix_profile and htm (HTM, the htmcore detector of the NAB community). The suffix
/field means the method watches each field (a warning names the field); /error means it watches the error of an online model of the
response. The text after "|" is the configuration; "detector|default" is the detector with its single configuration.

## Known limitations and caveats

These are limits of the benchmark and of how its rows can be read, not the declared limits of the detector (above). None of them
changes a row of the table. The number in brackets is the item in paineis/RESSALVAS.md, where each one has its origin and status.

How the table was built
- **Who wrote the series.** The synthetic streams (S rows) and the simulated company (M rows) were written by the same people who
  wrote the detector, around the claims it makes. They test whether the detector does what it claims; on the public bases (P rows),
  which nobody here wrote, the detector fails every row that decides.
- **Choice of the competitor configuration** [41]. Each competitor cell is the better of two configurations (the default and the one
  tuned on a separate development set), chosen after the approval run, as the protocol does for the best competitor of a row; the
  detector has one configuration. This is conservative for the detector's wins and weighs on the rows it lost or tied (M1 loses by
  0.300 with 2 standard errors of 0.284). The tuned configurations were chosen by detection alone, without the nulls (protocol,
  section 4.3), so a tuned configuration can go over the null ceiling and drop out of a row.
- **Adapter defects in two competitors** [1, 2]. CJSD cannot warn without a response: its calibration leaves tau empty and the input
  branch only runs when tau exists (competitors/methods.py, cjsd), so its zeros on the public bases and on the company are not a
  measure. The weighted WATCH adapter fits its scale on the whole series and uses later items at the start of the target
  (_watch_segment), so it is not strictly causal after the first input alarm. No verdict depends on either: WATCH and CTM go over the
  null ceilings of the synthetic rows with both configurations (with the Shiryaev-Roberts threshold of the WATCH paper, 10^4, on
  series of 18,000 scored items; ERRATA.md, entry 1, checks the copied code and runs them with the martingale threshold alone); where CJSD is the best allowed competitor without a response (P4 and P4L4), P4 fails on the
  detector's own null and P4L4 is a limit row, outside the verdict. Both fixes are for version 2.
- **Error axis** [30]. The competitors on the error axis watch the 0/1 error of an online model; the detector uses its own
  discretized reference. Their inputs are not identical.
- **"Tied"** [15] is the operational rule of the protocol (difference within two standard errors), not a test of equivalence. In M2
  the tie comes from a standard error of zero (every method at 6 of 6), the degenerate case.
- **The "e-values" of the detector** [18] are Bayes factors that restart when the evidence stops being positive; they are not e-values
  in the strict sense, and A = 200,000 does not give a 1/A guarantee of false alarm. The name stays in the frozen code and protocol.

Independence and uncertainty
- **The 2,047 series** [23] include shuffled copies, warm-up variants and processes of the same company life; they are not 2,047
  independent bases.
- **The simulated company** [22] has three lives plus variants of the first; processes, episodes and the incident repeated in the
  variants are not independent observations, and binomial intervals do not capture that. M2 "6 of 6" covers at most 4 independent
  incidents (4 of the 6 lives share a seed) [49].
- **Small rows** [29]. Binomial intervals: 7 of 10 goes from about 35% to 93%; 10 of 15, from 38% to 88%.
- **One approval run.** Each row is decided at two standard errors on its own, with no correction for the 18 rows that decide.

What each row measures
- **S3 where** [7] counts a hit when every accused field is true; it does not ask for all of them. Exact equality of the set: 308 of
  480; in ramp_all (20 fields change), the mean coverage is 6.17%. The errors: one series with no warning (sea_gradual) and one with a
  wrong field.
- **S4a direction** [5]. The right answer is fixed in the 209 cases scored: in the 179 numeric fields the rule of metrics/rows.py
  counts "up" as right, and in the 30 categorical ones it counts category 0 gaining share. A constant answer would also score 1.000;
  the row does not test falls.
- **S4b size** [6] is read 500 items after the warning, given a valid warning and the first true field with a report; it is not the
  size at the instant of the warning.
- **M3 regime change** [3] accepts the same "became the new normal" record for several changes of the same field: the 10 hits rest
  on 6 distinct records, counted per life. The variants repeat the regime change of the first life (same seed), which is real
  dependence; in the life with the shuffled calendar the detector hit none of its 3 targets.
- **M5 return** [10, 50]. "After the outage" in the label means after the defect goes off the air, that is, after the recovery
  (metrics/rows.py). Observed returns: 5 of 7 in 11 to 14 hours (681 to 815 min), none within 3 hours. The null measures "returned
  between 60 and 240 minutes after opening", which is not the same definition as the target; the row fails either way.
- **Event F1** [14] uses its own windows (several warnings in one window count one event; extended windows on SMD, SMAP and MSL); it is
  not comparable with the point-wise F1 of other work. With warnings restricted to the labeled duration, the detector's F1 goes from
  0.063 to 0.045 on SMD, from 0.091 to 0.083 on SMAP and from 0.222 to 0.157 on MSL.
- **NAB "24 of 43"** [28]: 43 is the number of events reachable after the warm-up, in 30 series; 12 events fall inside the warm-up and
  6 of the 36 approval series are shorter than it. The set has about 72 events (P1c: 66 in 36 series with a warm-up of 500, plus 6 out
  of reach).
- **SMD L4** [13]: the detector finds 9 of 127 short events; the only allowed competitor is CJSD, so the label "not confirmed" depends
  on its defect. The detector's null is not applied in limit rows, which is why it fails P4 on the null and not P4L4.

What the table does not show
- **Autocorrelation** [16]. On stationary AR(1) series with no change, the detector writes logs (tens to hundreds per series with a
  high rho) and no alert. The nulls of the protocol do not cover this case.
- **The extra warnings on the public bases** [17], in the training stretch, may be unlabeled changes or a reaction to
  autocorrelation; neither is shown, and the zero on the shuffled copies does not separate the two.
- **"Answers everything"** [12] holds for the methods and adapters of this benchmark, as output formats implemented here; it is not
  exclusivity in the whole field, nor quality proven on every dimension.
- **Intended use, not tested** [19]: "retrain if the relation broke, keep the model if only the input changed" and "next to an anomaly
  detector".
- **Dates** [21]. A hash proves content, not date. The original version of this repository is commit db2b946 (14/10/2026) in its history; the original
  Portuguese approval code is not published file by file.
- UCR and Yahoo S5 are not part of the benchmark; no deep-learning detector was run; HTM runs a later htm.core than its published
  threshold and score (protocol, section 10, v2, item 14).

## Related work

- **Benchmarks.** NAB (Lavin and Ahmad, "Evaluating Real-time Anomaly Detection Algorithms: the Numenta Anomaly Benchmark", IEEE ICMLA
  2015) gives the event windows and the score of P1. SMD comes from Su et al. (KDD 2019, OmniAnomaly), SMAP and MSL from Hundman et
  al. (KDD 2018, telemanom). Wu and Keogh ("Current Time Series Anomaly Detection Benchmarks are Flawed and are Creating the Illusion
  of Progress", IEEE TKDE, 2023) describe flaws of these bases, such as trivial events and doubtful labels; the P rows inherit them. Van
  den Burg and Williams ("An Evaluation of Change Point Detection Algorithms", arXiv 2003.06222, 2020) benchmark offline change point
  detection; this benchmark is online and per field.
- **Drift and change detectors.** Page-Hinkley (Page, Biometrika, 1954), DDM (Gama et al., SBIA 2004), ADWIN (Bifet and Gavalda, SDM
  2007), HDDM (Frias-Blanco et al., IEEE TKDE, 2015) and KSWIN (Raab, Heusinger and Schleif, Neurocomputing, 2020), all run from River
  (Montiel et al., JMLR, 2021). The split between a change in the input and a change in the relation with the response is the
  "virtual" and "real" drift of the concept drift literature (Gama et al., "A Survey on Concept Drift Adaptation", ACM Computing
  Surveys, 2014).
- **Real versus virtual drift, online.** The split between an alert (the relation with the outcome broke) and a log (only the input
  moved) is not new. Oda's CJSD ("Separating Covariate Shift from Mechanism Change with Two Discriminators", arXiv 2608.19885, 2026)
  splits a dataset difference exactly into a covariate axis and a functional axis, and a companion preprint by the same author ("What
  Changed? Drift Detection with Real, Virtual, and Incomparable Diagnosis", arXiv 2609.27865) uses the two axes to tell real, virtual
  and incomparable drift apart. CJSD is one of the 15 competitors
  here. Both preprints have a single author and were not peer reviewed when this benchmark ran. What the detector adds is doing the
  split per field, online, and naming the field whose relation broke; its per-field relation axis looks at P(y | x_j), not P(y | X),
  so a change that lives only in an interaction of fields is missed (limit L3, XOR).
- **Per-field CUSUM.** One two-sided CUSUM per field, with Page's last-zero estimate of the start, already gives which field, since
  when, which way and, from the mean after the shift, how much; the runner here reports only the field and the start for CUSUM.
- **Conformal test martingales.** Vovk et al. ("Retrain or not retrain: Conformal test martingales for change-point detection", COPA
  2021, PMLR 152) and WATCH (Prinster, Han, Liu and Saria, "WATCH: Adaptive Monitoring for AI Deployments via Weighted-Conformal
  Martingales", ICML 2025, PMLR 267), whose code runs here unchanged.
- **Other methods in the table.** Isolation forest (Liu, Ting and Zhou, ICDM 2008), the matrix profile (Yeh et al., ICDM 2016) and HTM
  (Ahmad et al., "Unsupervised real-time anomaly detection for streaming data", Neurocomputing, 2017).

## Errata

Errors and findings reported after publication are in ERRATA.md, each with its date, what was checked, what was found and whether any
row of the table changes. The frozen results are never edited in place: a correction that changes a number is a new run under a new
version of the protocol. To report an error, open an issue in this repository.

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
