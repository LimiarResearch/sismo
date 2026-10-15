# Public benchmark of the detector: protocol

Version 2, written on 2026-10-12 after the development run and before the approval frozen file. Version 1 was written on 2026-10-12,
before any run of any method on the data of this benchmark. Each version holds once its frozen file (section 9) is written. Any change
after that is a new version, in writing, with its justification, before running again; section 10 lists every version and what changed
in each.

The protocol was written in Portuguese. This is its English translation, made for publication after the approval run, with the names
of files, methods, streams and rows updated to the publication code (section 10, "Publication").

## 1. What is proven

At each instant the detector receives the values of a set of fields and, when there is one, the response y of a model. It claims:

| | claim | where it is measured |
|---|---|---|
| A1 | where: which field left its normal, among N fields | synthetic (S3), SMD (P4o), company (M1, M2) |
| A2 | when: the instant the change started (the start it attributes) and the latency of the warning | every row (reported), company (M2, decides) |
| A3 | what: up or down; how much, in standard deviations of the field's normal; the trajectory (stopped growing, came back, was replaced, became the new normal) | synthetic (S4), company (M3, M5) |
| A4 | alert and log: with a response, it separates a relation that broke (alert) from an input that changed (log) | synthetic (S1, S2) |
| A5 | slow drift: kept in the log, without an alert; when it stops, it becomes the new normal | synthetic (S5), company (M4) |
| A6 | few false warnings: on a series without a change, few warnings | the null of every row and S7 |

Limits declared before this benchmark. They are included to be measured; their rows are reported in the table and do not count in the
verdict:
- L1: a relation that breaks in the middle of a slow drift of the same part (the order rule holds the alert back);
- L2: real categorical change: the change is only in the combination of categories;
- L3: XOR: the change is only in the mechanism, with no change in the margins;
- L4: an isolated spike, of one to a few items: with 8 quantile bins per field, the spike falls in the top bin, which already receives
  12.5% of the normal items; one item there is worth about 2 nats, and a warning needs about 18 nats in one bin (with 38 fields). On the
  public bases, the events shorter than 10 items are reported apart as an L4 row and leave the row that decides. Every public base
  reports its L4 row (P1L4, P4L4, P5L4, P6L4); when a base has no event shorter than 10 items, the row shows n = 0 (NAB has none,
  because its events are label windows).

Another limitation: the warm-up. The detector learns from the first 2,000 items and does not warn before item 2,176. In the rows that
decide, every method uses the same warm-up; an information-only row ("P1c NAB (warmup500, information only): event F1") shows its price
(section 6).

## 2. The detector that runs

- The detector in detector/: a decision per bin (8 quantile bins per field, learned in the warm-up), a two-sample Bayes factor per bin,
  the mean of the e-values against A = 200,000, the input axis (log) and the relation axis (alert) with the order rule; after a log, the
  input reference is rebuilt in every bin; the live record (phases 0, 200 and 500); the trajectories.
- Parameters: its default parameters, the same on every row, with no tuning: warm-up W = 2,000, 8 bins, A = 200,000, minimum warm-up per
  bin 176 items, K = 2 when there is no response, trajectories with H = 5,000, window 300, step 100, base 1,000. It has no tuned
  configuration.
- Without a response (public bases and company), y = 0 on every item: only the input axis acts, and no alert is possible.
- A field that starts flat (fewer than 3 distinct edges among the bins of the warm-up): the scale ladder from the declared minimum unit,
  as the detector defines it (detector/monitor.py). On the public bases, the minimum unit of each field is the smallest positive
  difference between distinct values of the field in the warm-up (1.0 if the field is constant there). In the company, by the name of
  the field: "em %" (in %) 0.5; "em horas" (in hours) 0.1; anything else 1.0. The minimum unit is also the smallest standard deviation
  of the normal in the trajectories.
- A series is one monitor (one part): the synthetic stream, the NAB series, the SMD machine, the SMAP or MSL channel, and each of the
  131 processes of the company.
- The warning of the detector is the phase 0 record. Where: the accused fields. When: the "since" (for an alert, which carries no
  "since", the instant of the warning). What: the direction and size of the phase 500 record and the events of the trajectory.

## 3. The data

### 3.1 Public (data/sources.json: pinned origin and sha256 of every file; data/download.py downloads and checks)

| base | origin | what the truth marks | what it does not mark |
|---|---|---|---|
| NAB | numenta/NAB, commit ea702d7: 58 series, 365,558 points, 116 windows, the labeled points | one window per anomaly; the labeled point (for the latency) | where, direction, size, trajectory |
| SMD | NetManAIOps/OmniAnomaly, commit 7fb0e0a: 28 machines, 38 fields, train and test, 327 events | point by point on the test; per event, the fields that explain it | direction, size, trajectory |
| SMAP and MSL | the telemanom data; the original address denies access, and the mirror is imperial-qore/TranAD, commit 7ffb98d, data/SMAP_MSL; the labels have the same sha256 as the original (khundman/telemanom, commit 2e6c5b6), checked | the anomalous stretches of each channel and their class (point or contextual) | where inside the channel, direction, size |

UCR and Yahoo S5 are not part of this benchmark (the Yahoo S5 series, of 1,420 to 1,680 points, are also shorter than the warm-up).

Assembly: an SMD, SMAP or MSL series is the training part followed by the test part; the scored stretch is the test (from the later of
the end of training and the end of the warm-up); the training stretch after the warm-up is a null. A NAB series is scored from the end
of the warm-up.

### 3.2 Ours

- Synthetic streams (generators/synthetic.py): 20,000 items, change at T = 10,000, truth of kind, fields, direction and size.
  - relation breaks (REL): sea, sea_large, sea_gradual, stagger, num_real, num_imbalanced, num_noisy, mc_real, mc_cat;
  - input changes (ENT): cov, cov_gradual, num_cov, cat_cov, mc_cov, slow_abrupt, ramp_all;
  - slow drift with no change in the relation: slow_all, slow_few;
  - limits: slow_real (L1), cat_real (L2), xor (L3);
  - nulls (NUL): null_sea, null_num, null_cat, null_mc, slow_null, null_xor.
- The simulated company (generators/company/, the world of the contract in generators/company/CONTRACT.md): 131 processes, 495 fields,
  one item per minute, 30 days per life (43,200 minutes). The truth is in verdade.json; the "where" of each item of the truth follows
  runner/company.py. The process and field names, the life names and the truth are Portuguese data (glossary in
  generators/company/README.md).

### 3.3 Nulls

- Synthetic: the null streams and, for 10 seeds of each stream with a change, the same stream with the order of the items shuffled (3
  seeds in development).
- NAB: every approval series, shuffled. SMD, SMAP, MSL: the training stretch after the warm-up and, on a third of the series chosen by
  the hash of the name (int(sha256(name)[8:16], 16) % 3 == 0), the shuffled series; every series in development.
- Company: the null lives of the contract (no defect, shuffled and no drift; folders sem_defeito, embaralhado and sem_deriva), with the
  seed of the first normal life.

### 3.4 Development and approval (disjoint, declared now)

- Public bases: a series (file, machine, channel) belongs to development when int(sha256(name)[:8], 16) % 3 == 0; the others, to
  approval. NAB: 22 and 36; SMD: 8 and 20; SMAP: 20 and 35; MSL: 12 and 15.
- Synthetic: development on the seeds 20,000 to 20,009; approval on 30 seeds per stream drawn from the frozen file (section 9).
- Company: development on seed 1 (a normal life of 30 days and the three nulls); approval on 3 seeds drawn from the frozen file, 30
  days each, and the three nulls with the first of them.

## 4. The competitors

All of them run in this runner (competitors/methods.py), on the same series, with the same warm-up, on the same machine and in the same
environment (section 9). Each in two configurations: the default (of the library or of the paper) and the tuned one (section 4.3).
There are 15 competitor methods: page_hinkley, cusum, ewma, adwin, kswin, ddm, hddm_a, hddm_w, per_field_test, cjsd, watch, ctm,
isolation_forest, matrix_profile, htm.

### 4.1 List and adapters

| method | origin | default | how it enters |
|---|---|---|---|
| Page-Hinkley (page_hinkley) | river 0.26.1 | those of the library | per field, on the value standardized by the warm-up; with a response, also on the error of the model |
| two-sided (tabular) CUSUM (cusum) | the runner (Montgomery) | k = 0.5, h = 5 (in standard deviations of the warm-up); restarts after a warning; the start is the last zero of the sum | the same |
| EWMA control chart (ewma) | the runner | lambda = 0.2, L = 3; restarts after a warning | the same |
| ADWIN (adwin) | river 0.26.1 | delta = 0.002 | the same |
| KSWIN (kswin) | river 0.26.1, in a fast version with the same random draw and the same computation (competitors/kswin_fast.py; alarms identical to river's on 24/24 test series, competitors/check_kswin.py) | those of the library, seed 1 | the same |
| DDM, HDDM_A, HDDM_W (ddm, hddm_a, hddm_w) | river 0.26.1 | those of the library | with a response: on the error of the model; per field: on the 0/1 indicator "value outside the range from 0.5% to 99.5% of the warm-up" (declared adapter) |
| per-field test (per_field_test) | scipy: KS (numbers) or chi-square (categories), Bonferroni alpha/d | reference = the warm-up; window 1,000 every 250; alpha 0.05 | every field |
| CJSD (cjsd) | a reimplementation (competitors/methods.py) | thresholds calibrated on the development nulls up to zero warnings | with a response: both axes; without a response: only the input axis (adapter) |
| WATCH (watch) | original code (aaronhan223/watch, commit 3d17fca: the whole martingales.py and calculate_p_values, unchanged, in competitors/watch_original/), adapted in competitors/methods.py | martingale 100 or Shiryaev-Roberts 10^4 | with a response: the martingale of the model, with the input martingale deciding the kind; without a response: only the input martingale (X-CTM) |
| CTM (ctm) | the same without the weighting (the baseline of the WATCH paper) | the same | with a response; without a response it does not apply (it would be the same as WATCH without a response) |
| isolation forest (isolation_forest) | scikit-learn 1.9.1 | 100 trees, contamination "auto", seed 1, fitted on the warm-up | the vector of fields (with a response, plus y) |
| matrix profile (matrix_profile) | stumpy 1.14.1, left profile (only the past) | m = 100; a warning when it exceeds the largest value of the warm-up | per field |
| HTM (htm) | htm.core (htm-community, commit 96309f4, built here by data/build_htm.sh) with the htmcore detector of the community NAB (commit 98cdba6), with its parameters (competitors/htm_nab.py) | threshold 0.5014 (that of its standard profile); fixed seed 1 (in the original the seed is random and two executions differ; fixing it is the only change, so that the hashes reproduce). The threshold and the published score (63.08) are from 2019 and 2020, from an earlier version of the htm.core likelihood; the current code is from 2021 (section 10, v2, item 14) | per field, only on NAB and on the telemetry field of SMAP and MSL; on the other bases, "not run here: cost" (about 6.6 s per 1,000 points per field) |

With a response, the error of the model is the 0/1 error of an online logistic regression with online standardization (river;
SoftmaxRegression with more than two classes): 1 if the prediction made before seeing y is wrong.

### 4.2 Common rules

- Kind: on the error of the model, the warning is an alert (the implied action is to retrain); per field, per-field test, isolation
  forest, matrix profile and HTM, a log; CJSD, WATCH and CTM state the kind. Without a response, every warning is a log.
- Where: the per-field methods accuse the fields that fired; CJSD, WATCH, CTM and the isolation forest do not name a field (in the
  company, they count at the process level).
- When: the instant of the warning; the detector and CUSUM use the start they attribute.
- Marks less than 10 items after the previous one, from the same method on the same series, belong to the same warning (the first),
  with the union of the fields.
- CJSD, WATCH and CTM start over after each warning with a new warm-up (the following items), as does the per-field test. In CJSD, the
  initial reference is the end of the warm-up (its last 1,000 items; with a warm-up shorter than 1,000, the first 1,000 items).

### 4.3 Tuned configuration

Grid search on the development part of the same base (runner/configs.py, GRID); choice by runner/tune.py:
- synthetic: event F1 on the row that the kind of the method serves (alert: S1; log: S2; both: the mean);
- NAB, SMD, SMAP, MSL: event F1 on the development series;
- company: the M1 sensitivity minus the M1 rate on the no-defect null;
- tie: fewer false warnings per 1,000 items; then the order of the grid.

The grid only runs on the series that the choice looks at; nulls and shuffled series run the default configuration in development.
Grids: Page-Hinkley threshold {5, 10, 20, 50, 100, 200} x delta {0.0005, 0.005, 0.05}; CUSUM k {0.25, 0.5, 1} x h {3, 4, 5, 8, 12};
EWMA lambda {0.05, 0.1, 0.2, 0.3} x L {2.5, 3, 3.5, 4}; ADWIN delta {1e-6, 1e-5, 1e-4, 0.002, 0.01, 0.05}; KSWIN alpha {1e-5, 1e-4,
0.005} x window {100, 300} (sample 30); DDM threshold {2, 3, 4, 5} x warm start {30, 100}; HDDM_A and HDDM_W confidence {1e-5, 1e-4,
1e-3, 1e-2}; per-field test alpha {0.001, 0.01, 0.05} x window {250, 500, 1,000} x step {50, 250}; CJSD quantiles {0.9, 0.99, 1} of
the nulls for tau and tau_x; WATCH and CTM martingale {20, 100, 1,000} x Shiryaev-Roberts {1e2, 1e3, 1e4, 1e5, 1e6}; isolation forest
default threshold or quantile {0.99, 0.995, 0.999, 0.9999} of the score in the warm-up; matrix profile m {100, 256} x threshold {the
largest of the warm-up, or mean + k standard deviations with k in 3, 4, 5, 6}; HTM threshold {0.5014, 0.5, 0.9, 0.99, 0.999, 0.9999}.
The chosen configurations are in protocol/tuned.json, in the approval frozen file.

## 5. The metrics (metrics/events.py)

- Event and tolerance window: NAB, the official window; SMD, SMAP and MSL, a labeled stretch, with window [start, end + max(10,
  duration)); synthetic, the change at T, with window [T, T + 2,000) for an alert ([T, T + 4,000) for the gradual streams and sea) and
  [T, T + 4,000) for a log; company, the windows of the row. An event whose window ends before the scored stretch is out of reach of
  every method and is counted apart.
- Sensitivity: events with at least one warning in the window over the events. Precision: detected events over (detected + warnings
  outside every window); several warnings in the same window count one event. Event F1. No "point adjust".
- Ignored stretches: in the streams slow_abrupt and slow_real, the logs before T (the slow drift is already an input change); in
  slow_all and slow_few, the logs of the whole stream (they are what S5 asks for).
- Latency: first warning in the window minus the start (on NAB, minus the labeled point), in items; median and quartiles.
- When: |attributed start - start|; hit within 500 items (synthetic and public), reported.
- False warnings per 1,000 items and per day (where there is a clock: NAB, SMD, company).
- Where: among the events with fields in the truth, the fraction detected with all accused fields true, with N alongside.
- NAB: NAB's own score (standard profile), by NAB's code (commit ea702d7), unchanged, in an environment of its own (pandas 1.5.3,
  numpy 1.26.4) (metrics/nab_score.py); each method becomes a detector with score 1 at the warning and threshold 0.5. Validated before
  running: the code, by the same path, recomputes the published score of the "numenta" detector (70.10105611945585 against
  70.10105611943965).
- Standard error: every proportion with n and binomial standard error; F1 and differences between methods by paired resampling of the
  series (or of the episodes, in the company), 1,000 resamples, seed 20261012.

## 6. The rows and the criteria (metrics/rows.py)

| row | data | main metric | null and ceiling |
|---|---|---|---|
| S1 relation breaks | REL | event F1 of the alerts | null and shuffled streams: runs with an alert <= 2% |
| S2 input changes | ENT | event F1 of the logs; the detector with an undue alert (an alert after T) <= 10% on each stream | runs with a log <= 5% |
| S3 where | REL and ENT with a field in the truth | detection with all accused fields true, among N (3, 10 or 20) | both ceilings |
| S4 what | ENT (detector only) | a) right direction; b) size within 0.25 sd of the true one (computed by the generators in the windows of the record itself); c) new normal on the true field after T, on the steps that stay | a) 50%; b) constant guess (the median of the true sizes); c) null streams with some new normal |
| S5 slow drift | slow_all, slow_few | runs with the drift in the log and no alert | alert <= 2% on the nulls |
| S6 limits | slow_real (L1), cat_real (L2), xor (L3) | F1 of the alerts; reported, outside the verdict | |
| S7 nulls | null and shuffled streams | runs with a warning from the detector | alert <= 2% and log <= 5% |
| P1 NAB, P4 SMD, P5 SMAP, P6 MSL | approval series, warm-up 2,000, without the events shorter than 10 items | event F1 | shuffled series and training stretch: warnings per 1,000 items <= 0.1 |
| P1L4, P4L4, P5L4, P6L4 | the events shorter than 10 items (limit L4); n = 0 shown when the base has none | sensitivity; reported, outside the verdict | |
| P4o SMD where | SMD events with the fields of the interpretation | detection with all accused fields true, among 38 | that of P4 |
| P1o NAB official (information) | by the NAB rules (warm-up = the NAB probationary period, 15% of the series and at most 750 items; the detector with its own warm-up of 2,000); each warning becomes score 1 at the item of the warning, threshold 0.5 (the threshold of each method is that of its configuration, not the one the NAB optimizer would choose on the whole corpus) | NAB score, standard profile: the approval series with both configurations; the 58 series with the default configurations; and the published score of HTM, cited with its origin | |
| P1c NAB warm-up 500 (information; label "P1c NAB (warmup500, information only): event F1") | approval series, a warm-up of 500 for every method, the detector included | event F1 | |
| M1 contingency | releases with a defect in the normal lives | warning on the error field of the affected route (or of another route of the component) within 60 min | no defect: releases with a warning on the set of these fields within 60 min <= 0.3 |
| M2 incident | incidents of every life | warning on the probe within 10 min and attributed start between 30 min before and 10 min after | 200 windows of 10 min per life, drawn outside the incidents: <= 0.3 |
| M3 regime change (detector only) | regime changes of every life | became the new normal on the latency field within 15 days | latency fields of routes without a change, in the same windows |
| M4 drift (detector only) | the portfolio | new normal in each normal life | none in the no-drift life |
| M5 return (detector only) | M1 episodes with an outage | returned to normal within 180 min after the outage | no defect: episodes opened on the error fields that return between 60 and 240 min after opening |

Verdict of each row with competitors, against the best competitor (the largest value of the metric among all methods and the two
configurations of each that respect the ceiling of the row's null): WON if the detector is above by more than 2 standard errors of the
difference; TIED within 2; LOST below by more than 2. A competitor whose null was not measured (this only happens in development, where
the grid does not run on the nulls) stays eligible. A row with only the detector: it passes only if the detector is above the null by
more than 2 standard errors. The detector's null above the ceiling fails the row. A row that decides with no data (n = 0 in the row or
in the null) comes out "no verdict" and does not pass. A declared limit row: reported, outside the verdict ("limit confirmed" if lost;
"not confirmed in this sample" if not). An information-only row: reported. Any other row where the detector loses: FAILED, recorded as
failed. The benchmark PASSES if every row that decides passes; the overall verdict is written in the table, with the rows that decide
and those that did not pass. The result of every row is published.

## 7. The runs

- Development, on the frozen file of this version: on the development sets, to find construction errors and for the grid search.
  Nothing from it counts as proof. Each construction error becomes a new version of this protocol, in writing, before the approval
  frozen file. It produces: the CJSD default thresholds (protocol/cjsd_default.json) and the tuned configurations (protocol/tuned.json).
- Approval: a single run, on the approval frozen file, with separate processes per series; each series writes its whole output to a
  file of its own and a line in the resume log; if the machine stops, the run continues from the series without an output, and the stop
  is recorded. One approval runs at a time per machine: the benchmark runs in an environment of its own, and nothing else runs in that
  environment during the approval. The detector
  does not change during the benchmark; no series and no competitor is removed after the result is seen.

## 8. What is not done

Tuning the detector; choosing series, seeds or windows after seeing results; removing a competitor that wins; using "point adjust" or
a metric that inflates; citing a number without the hash of the frozen file.

## 9. The frozen file

The sha256 of every file that measures goes into a frozen file, as an explicit list (a frozen file for development from protocol v1,
and one for approval). They were written by the code of that time, whose file names were Portuguese, and are kept unchanged in
protocol/history/ (see protocol/history/README.md). The approval frozen file (protocol/history/frozen_approval_original.sha256) holds:
this protocol; all the code (detector/, competitors/, runner/, metrics/, generators/, data/, without the downloaded data); the data
sources file (the sha256 of every data file); the environment file (Python and the versions of every package of both environments; the
sha256 of the built htm package is information only, because it changes at each build); requirements.txt and requirements-nab.txt; the
hash of the result of a check of the detector code; and, in the approval file, the CJSD default thresholds and the tuned
configurations. Left out: the documentation that receives the table after the run (README.md and the reproduction script), the run
logs and the outputs.

Approval seeds: for i = 0, 1, 2, ..., int(sha256(content of the approval frozen file + ":" + i)[:8], 16) % 900,000 + 100,000, skipping
repeats; the first 30 for the synthetic streams and the next 3 for the company (runner/seeds.py; protocol/seeds.json, drawn from
protocol/history/frozen_approval_original.sha256).

The publication code (section 10, "Publication") has its own frozen file, protocol/frozen_publication.sha256, written by
runner/freeze.py: the code and data folders (without the *.md documentation, the downloaded data and the generated lives),
protocol/ENVIRONMENT.txt, protocol/cjsd_default.json, protocol/tuned.json, protocol/seeds.json, protocol/publication/keymap.json,
requirements.txt and requirements-nab.txt. reproduce.sh checks it before running.

## 10. Versions

- v1 (frozen_v1.sha256, 2026-10-12): the version above.
- v1.1 (2026-10-12, before any run on v1): the environment record (then AMBIENTE.txt, now protocol/ENVIRONMENT.txt) came out with the
  line of the htm package broken and with the local path of the build; the freezing script now writes "htm==2.2.0 (built by
  data/build_htm.sh; sha256 of the package)". No rule, computation or parameter changes. Frozen file: frozen_v1_1.sha256.
- v1.2 (2026-10-12, before any run): in the v1.1 frozen file the htm line came out without the sha256 of the package (the freezing
  script looked for it in the wrong path); the path of the package is now given to the freezing script. No rule, computation or
  parameter changes. Frozen file: frozen_v1_2.sha256. The development run runs on this version.
- v2 (2026-10-12, after the development run on v1.2 and before the approval frozen file). Construction errors found in development and
  corrected; no rule of the detector, no metric that decides, no ceiling and no series changes:
  1. data/build_htm.sh builds the example executables that the htm.core installation requires (found when building in a clean
     environment).
  2. The frozen file becomes an explicit list (section 9); the documentation that receives the table after the run is left out.
  3. The sha256 of the htm package changes at each build (the dates are stored in the package): rebuilt from scratch, the HTM scores on
     a test series with seed 1 are identical (same sha256 of the scores). The hash of the package is information only; the
     reproduction checks the warnings of every series, which include those of HTM.
  4. A row that decides with no data came out FAILED; it now comes out "no verdict" and does not pass (section 6).
  5. On SMD, the start and end of the events came out as numpy integers and writing the output failed; no written output changes.
  6. HTM on NAB: the runner passed synthetic instants instead of the real instants of the series (htmcore encodes the time of day); it
     now receives the real ones, and the NAB development outputs were redone. On the shuffled series, the instants stay in the original
     order.
  7. The summarizer of the rows also read the outputs of the CJSD calibration (without the detector); it now skips them.
  8. The overall verdict of the benchmark is written by the summarizer and in the table (the rule is that of section 6).
  9. On the public bases, the null of a configuration without a shuffled series run came out 0; it now comes out "not measured"
     (section 6).
  10. NAB official: the probationary period was 15% of the series; it is now NAB's (nab/util.py, getProbationPeriod: 15% of the series
      and at most 750 items). The outputs of the official variant in development were redone.
  11. NAB official on the 58 series with the default configurations: v1 required it and the runner did not do it (it ran only the
      series of the part, and the default configuration filter did not work). In the approval, the official variant runs on the 58
      series.
  12. The text of section 7 is reworded: it now says only that the benchmark runs in an environment of its own.
  13. The table is also written in English, with the names of the rows translated.
  14. HTM checked against the published score (competitors/check_htm.py): the port reproduces htmcore of commit 98cdba6 with htm.core
      96309f4; on the 58 series, with seed 1, the raw scores scored as NAB scores them give -22.27 on the standard profile, and the
      same scores turned into warnings as in the benchmark give 34.94. The published score, 63.08, and the default threshold, 0.5014,
      are from 2019 and 2020 (commits 3097a72 and 2c305b2), from the old likelihood; the detector moved to the new htm.core likelihood on
      2021-09-30 (commit 79e6054) without a new score. Nothing changes in the method or in the grid, which already has the thresholds
      from 0.9 to 0.9999; the table cites the published score with its origin. It was decided before the approval run not to build an
      old version of htm.core.
  15. Information added, without changing any verdict: in M5, the minutes between the outage and the first "returned to normal" of each
      episode; in the P rows, the null of each method split into shuffled series and training stretch.

  Seen in development and kept as it is (criterion written before running): M5 asks for "returned to normal" within 180 min after the
  outage; the detector says it in all 5 development episodes, from 661 to 731 min after. The M5 null is not measured when the detector
  opens no episode on the no-defect null (0 in development); the row comes out "no verdict". The null of the public bases stays as in v1
  (shuffled series and the training stretch after the warm-up). Frozen file: frozen_approval_original.sha256 (then
  congelado_aprovacao.sha256).
- Publication (2026-10-14, after the approval run). The protocol was first written in Portuguese and is translated here for publication;
  the code, its comments and the documentation were translated to English and cleaned. Files, methods, synthetic streams, configuration
  parameters and rows were renamed (old to new names in protocol/publication/keymap.json). No rule, computation, parameter, threshold or
  series changes. Every public base now reports its L4 row (section 1, L4), with n = 0 when the base has no event shorter than 10 items;
  in the approval run only P4L4 was written, because the other bases had no such event. The translation, the code cleanup, the defects
  fixed and the check of the publication code against the approval outputs are described in protocol/approval_record.md. Frozen file:
  protocol/frozen_publication.sha256.
