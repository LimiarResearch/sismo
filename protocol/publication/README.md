# Publication tools

The approval run used code whose names (files, folders, output keys, methods, synthetic streams, configuration parameters, row labels)
were Portuguese. The publication code uses English names. The files here translate between the two and check that the publication
code gives the same results as the approval run (protocol/approval_record.md, section "Publication version").

## keymap.json

The map from every old name (approval run) to the new one (publication code): output keys, bases, variants, parts, synthetic stream
types, methods and their modes, configuration parameters and labels, trajectory events, directions, run layout, runner options, the
keys of the protocol JSON files, the row labels and texts, and the keys of the NAB score. The values of the data are not renamed: the
series names of the public bases, the process and field names of the simulated company, the names of the lives and the files written
by the company generator stay as they are. keymap.json is part of the frozen file (protocol/frozen_publication.sha256), because
runner/legacy.py reads it.

## runner/legacy.py

Two names feed a hash whose order reaches the results, so the publication code computes them with the names of the approval run:
- the output file of a series (runner.run.output_file_name, the first 20 hex digits of the sha256 of "base|name|variant|seed"): the
  metrics read the outputs in file-name order, and the company rows resample the lives in the order in which they first appear;
- the NAB detector name of a method and configuration (metrics.nab_score.detector_name): NAB sums the per-file scores in the order of
  its directory listing, whose names start with the detector name, and the last digits of the scores depend on that order.

With these names, a run of the publication code writes the same output file names as the approval run. A method that is not in
keymap.json keeps its own name.

## compare_runs.py

Compares the outputs of the approval run with the outputs of a run of the publication code, series by series, after translating the
original outputs with keymap.json:

```
python protocol/publication/compare_runs.py <original_run_folder> <new_run_folder> [--sample] [--show N]
```

For each series ("base|variant|name|seed") it compares the series description, the warning lists of every method and configuration,
the detector outputs (warnings, phase 500 reports, trajectory events), the methods not run and the CJSD calibration log; machine time
is not compared. It prints the number of series compared, identical, different and missing on either side, and exits with status 1 on
any difference or missing series. --sample expects only the series present in the new run (useful for a partial run); --show N prints
the details of at most N differing series (default 20).

```
python protocol/publication/compare_runs.py --convert <original_run_folder> <output_folder>
```

writes the translated original outputs in the current schema, with the file names the runner writes, and links
<output_folder>/lives to the lives of the original run. The metrics can then be computed on the original outputs without running any
method (see README.md, "How to reproduce").

## compare_rows.py

Compares the rows (metrics/rows.py) and the NAB score (metrics/nab_score.py) of the approval run with those computed by the publication
code. Every value is compared exactly (numbers, lists, verdicts and statuses); row labels are matched through keymap.json; rows that
exist only in the new results (P1L4, P5L4, P6L4) are listed apart and are not an error.

```
python protocol/publication/compare_rows.py <original_rows.json> <new_rows.json> [--nab <original_nab.json> <new_nab.json>]
```

## Verifying the publication run against the original outputs

1. Get the original approval outputs (approval_original.zip at https://huggingface.co/datasets/LimiarResearch/sismo-benchmark-runs) and unpack them, which gives approval_original/.
2. Check the code against the frozen file:
   `cd protocol && sed 's#  #  ../#' frozen_publication.sha256 | sha256sum -c --quiet -`
3. Run the approval with the publication code and the same seeds (protocol/seeds.json):
   `sh runner/batch.sh <benchmark python> publication approval data/raw` (outputs in outputs/publication/).
4. Compare every series: `python protocol/publication/compare_runs.py approval_original outputs/publication`
5. Compute the rows and the NAB score of the new run and compare them with the original ones:
   ```
   python -m metrics.rows outputs/publication --lives outputs/publication/lives --json rows.json
   python -m metrics.nab_score outputs/publication/nab/official <nab_python> data/raw nab_work --json nab.json
   python protocol/publication/compare_rows.py approval_original/linhas.json rows.json --nab approval_original/nab.json nab.json
   ```
6. The table from the new rows (`python -m runner.table rows.json nab.json`) is results/publication/table.txt.
