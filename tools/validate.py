#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Validate an NDJSON stream against the observation or signal schema.

    python3 tools/validate.py examples/synthetic.sample.ndjson
    python3 tools/validate.py signals.ndjson --schema signal

Exit code is non-zero on any failure, so this drops straight into CI. An emitter that
breaks the contract should fail its own build, not a consumer's dashboard at 2am.
"""
import argparse, json, sys, pathlib

def load_schema(name):
    here = pathlib.Path(__file__).resolve().parent.parent
    return json.loads((here / "schema" / f"{name}.schema.json").read_text(encoding="utf-8"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--schema", default="observation", choices=["observation", "signal"])
    ap.add_argument("--max-errors", type=int, default=20)
    a = ap.parse_args()

    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("needs jsonschema 4.18 or newer (draft 2020-12 support):\n"
              "    pip install 'jsonschema>=4.18'", file=sys.stderr)
        return 2

    validator = Draft202012Validator(load_schema(a.schema))
    total = bad = 0
    types = {}

    with open(a.path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                bad += 1
                if bad <= a.max_errors:
                    print(f"line {n}: not JSON -- {e}")
                continue
            key = row.get("type", row.get("class", "?"))
            types[key] = types.get(key, 0) + 1
            for err in validator.iter_errors(row):
                bad += 1
                if bad <= a.max_errors:
                    loc = "/".join(str(x) for x in err.absolute_path) or "(root)"
                    print(f"line {n}: {loc}: {err.message}")

    print(f"\n{total:,} records, {bad} problem(s)")
    if a.schema == "observation" and total:
        verbal = sum(v for k, v in types.items() if str(k).startswith("communication."))
        print(f"non-verbal: {100*(total-verbal)/total:.1f}%")
    for k, v in sorted(types.items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {v:>7,}  {k}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
