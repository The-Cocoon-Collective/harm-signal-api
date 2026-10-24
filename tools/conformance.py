#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Conformance tests. Run them, publish the output, and that is the whole certification
process -- there is no committee and no fee.

    python3 tools/conformance.py stream.ndjson
    python3 tools/conformance.py signals.ndjson --schema signal --observations stream.ndjson

Four things are checked, and the second one is the one that matters:

  1. SCHEMA      every record validates.
  2. NO IDENTITY no record smuggles a person into a field that was not meant to hold one.
  3. EVIDENCE    every signal cites observations that exist, and says why in plain words.
  4. EXPIRY      every signal expires.

Check 2 exists because a schema can only stop the mistakes it can see. It has no field for
an email address, so nobody sets one -- but attributes is an open map, and content_ref is a
string, and both are exactly where a tired emitter puts a username at four in the afternoon.
So we go looking.

Exit code is non-zero on any failure. Wire it into your build.
"""

import argparse, json, pathlib, re, sys
from collections import Counter

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URLISH = re.compile(r"https?://|www\.", re.I)
PHONEISH = re.compile(r"(?:\+?\d[\s().-]?){9,}")
# a ref should look like a machine made it
OPAQUE = re.compile(r"^[A-Za-z0-9_.:-]{8,128}$")
WORDY = re.compile(r"^[A-Za-z][A-Za-z'’-]{2,}(?:\s+[A-Za-z'’-]{2,})+$")   # "Sam Baker"

MAX_FREE_TEXT = 24     # characters; above this an attribute string is not an enum any more


def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if line:
                rows.append((n, json.loads(line)))
    return rows


def refs_in(row):
    out = []
    for key in ("actor", "target", "subject"):
        if isinstance(row.get(key), dict) and "ref" in row[key]:
            out.append((key, row[key]["ref"]))
    for i, c in enumerate(row.get("co_present", []) or []):
        out.append((f"co_present[{i}]", c["ref"]))
    for i, c in enumerate(row.get("counterparties", []) or []):
        out.append((f"counterparties[{i}]", c["ref"]))
    return out


def identity_problems(row):
    bad = []
    for where, ref in refs_in(row):
        if EMAIL.search(ref) or "@" in ref:
            bad.append(f"{where}.ref looks like an email address")
        elif not OPAQUE.match(ref):
            bad.append(f"{where}.ref is not opaque")
        elif WORDY.match(ref.replace("_", " ")):
            bad.append(f"{where}.ref reads like a name")

    for k, v in (row.get("attributes") or {}).items():
        if isinstance(v, str):
            if EMAIL.search(v):
                bad.append(f"attributes.{k} contains an email address")
            elif URLISH.search(v):
                bad.append(f"attributes.{k} contains a URL")
            elif PHONEISH.search(v):
                bad.append(f"attributes.{k} contains something shaped like a phone number")
            elif len(v) > MAX_FREE_TEXT:
                bad.append(f"attributes.{k} is {len(v)} characters -- free text, not an enum")
    cr = row.get("content_ref")
    if isinstance(cr, str):
        if EMAIL.search(cr) or URLISH.search(cr):
            bad.append("content_ref carries content or a locator, not an opaque pointer")
        if " " in cr:
            bad.append("content_ref contains spaces -- that is a message, not a pointer")
    return bad


def main():
    ap = argparse.ArgumentParser(description="Conformance tests for a harm-signal stream.")
    ap.add_argument("path")
    ap.add_argument("--schema", default="observation", choices=["observation", "signal"])
    ap.add_argument("--observations", help="for signals: the stream they were drawn from")
    ap.add_argument("--max-report", type=int, default=15)
    a = ap.parse_args()

    here = pathlib.Path(__file__).resolve().parent.parent
    schema = json.loads((here / "schema" / f"{a.schema}.schema.json").read_text(encoding="utf-8"))
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("needs jsonschema 4.18 or newer (draft 2020-12 support):\n"
              "    pip install 'jsonschema>=4.18'", file=sys.stderr)
        return 2
    validator = Draft202012Validator(schema)

    known = set()
    if a.observations:
        known = {o["observation_id"] for _, o in load(a.observations)}

    rows = load(a.path)
    failures = Counter()
    reported = 0

    def fail(check, line, message):
        nonlocal reported
        failures[check] += 1
        if reported < a.max_report:
            reported += 1
            print(f"  line {line}: [{check}] {message}")

    print(f"checking {len(rows):,} {a.schema} record(s) in {a.path}\n")

    for n, row in rows:
        for err in validator.iter_errors(row):
            loc = "/".join(str(x) for x in err.absolute_path) or "(root)"
            fail("schema", n, f"{loc}: {err.message}")
        for problem in identity_problems(row):
            fail("no-identity", n, problem)
        if a.schema == "signal":
            ev = row.get("evidence") or []
            if not ev:
                fail("evidence", n, "signal cites no observations")
            elif known:
                missing = [e for e in ev if e not in known]
                if missing:
                    fail("evidence", n,
                         f"cites {len(missing)} observation id(s) not in the stream, "
                         f"e.g. {missing[0]}")
            r = (row.get("rationale") or "").strip()
            if len(r) < 20 or not any(c.isalpha() for c in r):
                fail("evidence", n, "rationale is not a sentence a person could read")
            if not row.get("expires_at"):
                fail("expiry", n, "signal has no expires_at -- it would become permanent")

    checks = ["schema", "no-identity", "evidence", "expiry"] if a.schema == "signal" \
             else ["schema", "no-identity"]
    print()
    for c in checks:
        n = failures[c]
        print(f"  {'PASS' if n == 0 else 'FAIL'}  {c:<12} {'' if n == 0 else f'{n} problem(s)'}")
    total = sum(failures.values())
    if total > reported:
        print(f"\n  ({total - reported} further problem(s) not shown)")
    print(f"\n{'CONFORMANT' if total == 0 else 'NOT CONFORMANT'} "
          f"at schema version {schema['properties']['schema_version']['const']}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
