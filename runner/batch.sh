#!/bin/sh
# The runs of the benchmark (protocol, section 7). Usage: runner/batch.sh <python> <run> <development|approval> [raw_data_dir]
# Generates the lives of the simulated company (at most 4 at a time), then runs four processes, each with its own series (i % 4 == k)
# on every base; a series whose output is already written does not run again (resume). Outputs go to outputs/<run>/.
set -e
PY=$1; RUN=$2; PART=$3; RAW=${4:-data/raw}
[ -n "$PY" ] && [ -n "$RUN" ] && [ -n "$PART" ] || { echo "usage: $0 <python> <run> <development|approval> [raw_data_dir]" >&2; exit 1; }
case "$PART" in development|approval) ;; *) echo "batch.sh: part must be development or approval, not '$PART'" >&2; exit 1 ;; esac
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMBA_NUM_THREADS=1 PYTHONHASHSEED=0
cd "$(dirname "$0")/.."
S=outputs/$RUN; V=$S/lives; mkdir -p "$V"

# wait_all <pids>: waits for every process and fails if any of them failed
wait_all() {
  failed=0
  for pid in "$@"; do
    wait "$pid" || failed=1
  done
  [ "$failed" -eq 0 ] || { echo "batch.sh: a background step failed (see $S/log.txt)" >&2; exit 1; }
}

# The lives: <folder name>:<seed>:<null mode of the generator, empty for a normal life>. The folder names are part of the series
# names of the company (and so of the seeds of WATCH); the null modes are those of generators/company/run.py.
if [ "$PART" = development ]; then
  LIVES="normal_s1:1: sem_defeito_s1:1:sem_defeito embaralhado_s1:1:embaralhado sem_deriva_s1:1:sem_deriva"; CFG=grid
else
  E=$("$PY" -c "import json; print(' '.join(map(str, json.load(open('protocol/seeds.json'))['company'])))")
  set -- $E
  LIVES="normal_s$1:$1: normal_s$2:$2: normal_s$3:$3: sem_defeito_s$1:$1:sem_defeito embaralhado_s$1:$1:embaralhado sem_deriva_s$1:$1:sem_deriva"; CFG=approval
fi
echo "$(date -u +%FT%TZ) start $RUN $PART" >> "$S/log.txt"
running=0; pids=""
for v in $LIVES; do
  name=${v%%:*}; rest=${v#*:}; seed=${rest%%:*}; null=${rest#*:}
  ( "$PY" -c "import sys; sys.path.insert(0, '.'); from runner.company import generate; generate('$V/$name', 30, $seed, '$null' or None, '$PY')" \
      && echo "$(date -u +%FT%TZ) life $name" >> "$S/log.txt" ) &
  pids="$pids $!"; running=$((running + 1))
  if [ "$running" -ge 4 ]; then
    wait_all $pids; running=0; pids=""
  fi
done
wait_all $pids
BASES="synthetic nab smd smap msl company"
if [ "$PART" = development ] && [ ! -s protocol/cjsd_default.json ]; then
  pids=""
  for k in 0 1 2 3; do
    ( for b in $BASES; do "$PY" -m runner.run "$RUN" $b "$PART" --calibrate-cjsd --process $k --of 4 --raw "$RAW" --lives "$V" || exit 1; done ) &
    pids="$pids $!"
  done
  wait_all $pids
  "$PY" -m runner.calibrate_cjsd "$S" >> "$S/log.txt"
fi
pids=""
for k in 0 1 2 3; do
  ( for b in $BASES; do "$PY" -m runner.run "$RUN" $b "$PART" --configs $CFG --process $k --of 4 --raw "$RAW" --lives "$V" || exit 1; done
    for var in official warmup500; do "$PY" -m runner.run "$RUN" nab "$PART" --variant $var --configs $CFG --process $k --of 4 --raw "$RAW" || exit 1; done ) &
  pids="$pids $!"
done
wait_all $pids
echo "$(date -u +%FT%TZ) end $RUN $PART" >> "$S/log.txt"
