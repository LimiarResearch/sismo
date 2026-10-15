#!/bin/sh
# Reproduces the whole benchmark with one command and checks the hashes and the table against the published ones.
# Requirements: Linux, Python 3.11, uv, git, cmake, g++, curl, unzip. About 15 hours on a machine with 4 cores and 15 GB of memory.
# Usage: ./reproduce.sh [work_folder]   (default: ./work; the outputs go to outputs/reproduction/)
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"; W="${1:-$ROOT/work}"; mkdir -p "$W"; W="$(cd "$W" && pwd)"; cd "$ROOT"

fail() { echo "reproduce.sh: FAILED: $*" >&2; exit 1; }
need() { command -v "$1" > /dev/null 2>&1 || fail "$1 not found (needed: $2)"; }

echo "0. requirements"
need python3.11 "the benchmark environments"; need uv "the benchmark environments"; need sha256sum "the frozen file check"
need git "the htm.core build"; need cmake "the htm.core build"; need g++ "the htm.core build"; need curl "the htm.core build"
need unzip "the htm.core build"
PY311=$(command -v python3.11)

echo "1. environments (pinned versions)"
[ -x "$W/benchmark/bin/python" ] || { uv venv -q -p "$PY311" "$W/benchmark" && uv pip install -q --python "$W/benchmark/bin/python" -r requirements.txt; } \
  || fail "could not create the benchmark environment"
[ -x "$W/nab/bin/python" ] || { uv venv -q -p "$PY311" "$W/nab" && uv pip install -q --python "$W/nab/bin/python" -r requirements-nab.txt; } \
  || fail "could not create the NAB environment"
PY="$W/benchmark/bin/python"; PYNAB="$W/nab/bin/python"
"$PY" -c "import htm" 2>/dev/null || sh data/build_htm.sh "$PY" "$W/htm" || fail "could not build htm.core"
"$PY" -c "import htm" 2>/dev/null || fail "the htm package is not importable after the build"

echo "2. public data (pinned origin, sha256 checked)"
# data/raw may be a real folder that already holds the data (it is checked and completed in place), a link, or missing (then the data
# goes to the work folder and data/raw links to it).
if [ -d data/raw ] && [ ! -L data/raw ]; then
  RAW="$ROOT/data/raw"
elif [ -e data/raw ] && [ ! -L data/raw ]; then
  fail "data/raw exists and is not a folder; move it away"
else
  RAW="$W/raw"; mkdir -p "$RAW"; ln -sfn "$RAW" data/raw || fail "could not link data/raw to $RAW"
fi
"$PY" data/download.py "$RAW" --bases nab,smd,smap_msl,nab_code,label_check || fail "public data download or sha256 check"

echo "3. the frozen file"
[ -s protocol/frozen_publication.sha256 ] || fail "protocol/frozen_publication.sha256 is missing"
( cd protocol && sed 's#  #  ../#' frozen_publication.sha256 | sha256sum -c --quiet - ) || fail "files differ from protocol/frozen_publication.sha256"
echo "   frozen file checked"

echo "4. the approval run (lives of the company, every base; resumes where it stopped)"
sh runner/batch.sh "$PY" reproduction approval "$RAW" || fail "the run"

echo "5. the warning lists of each series against the published ones"
[ -s protocol/publication_warnings.sha256 ] || fail "protocol/publication_warnings.sha256 is missing"
"$PY" -m runner.warnings_manifest outputs/reproduction > "$W/warnings_reproduction.sha256" || fail "the warnings manifest"
diff -q protocol/publication_warnings.sha256 "$W/warnings_reproduction.sha256" > /dev/null \
  || fail "warning lists differ from protocol/publication_warnings.sha256 (see diff protocol/publication_warnings.sha256 $W/warnings_reproduction.sha256)"
echo "   warnings identical to the published ones"

echo "6. the rows, the NAB score and the table"
"$PY" -m metrics.rows outputs/reproduction --lives outputs/reproduction/lives --json "$W/rows.json" > /dev/null || fail "the rows"
"$PY" -m metrics.nab_score outputs/reproduction/nab/official "$PYNAB" "$RAW" "$W/nab_score" --json "$W/nab.json" > /dev/null || fail "the NAB score"
"$PY" -m runner.table "$W/rows.json" "$W/nab.json" > "$W/table.md" || fail "the table"
diff -q results/publication/table.txt "$W/table.md" > /dev/null || fail "the table differs from the published one (see diff results/publication/table.txt $W/table.md)"
echo "   table equal to the published one (results/publication/table.txt)"
echo "reproduced"
