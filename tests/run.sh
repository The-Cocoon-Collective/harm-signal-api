#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Everything this repository claims, checked in one command.
#   ./tests/run.sh
set -euo pipefail
cd "$(dirname "$0")/.."
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

say() { printf '\n=== %s\n' "$1"; }

say "generate"
python3 tools/synth.py --days 30 --participants 40 --seed 7 --out "$WORK/s.ndjson"

say "validate observations"
python3 tools/validate.py "$WORK/s.ndjson" | tail -5

say "conformance, observations"
python3 tools/conformance.py "$WORK/s.ndjson" | tail -5

say "baseline analyzer (deliberately weak)"
python3 tools/example_analyzer.py "$WORK/s.ndjson" --out "$WORK/base.ndjson" >/dev/null
python3 tools/score.py "$WORK/base.ndjson" "$WORK/s.ndjson.answers.json" | tail -1

say "structural analyzer"
python3 analyzers/structural.py "$WORK/s.ndjson" --out "$WORK/sig.ndjson"
python3 tools/score.py "$WORK/sig.ndjson" "$WORK/s.ndjson.answers.json" | tail -1

say "validate signals"
python3 tools/validate.py "$WORK/sig.ndjson" --schema signal | tail -3

say "conformance, signals"
python3 tools/conformance.py "$WORK/sig.ndjson" --schema signal \
        --observations "$WORK/s.ndjson" | tail -8

say "anonymise"
python3 tools/anonymise.py "$WORK/s.ndjson" --out "$WORK/anon.ndjson" --k 20 | tail -8
python3 tools/validate.py "$WORK/anon.ndjson" | tail -3

say "fit, then generate from the fit"
python3 tools/fit.py "$WORK/s.ndjson" --epsilon 1.0 --k 20 --seed 1 --out "$WORK/params.json" | tail -4
python3 tools/synth.py --params "$WORK/params.json" --days 30 --participants 40 --seed 9 \
        --out "$WORK/like.ndjson" | tail -4
python3 tools/validate.py "$WORK/like.ndjson" | tail -3

printf '\nall checks ran\n'
