#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Turn a pseudonymous observation stream into something that can leave the building.

    python3 tools/anonymise.py synthetic.ndjson --out anon.ndjson --k 20

What it does, and why each step is there, is written out in PRIVACY.md. The short version:
re-key the refs under a fresh epoch key, generalise time and place, drop content, bucket
the numbers, then suppress any cell that rests on fewer than k distinct participants.

Read the report it prints. An anonymiser whose losses you cannot see is a claim, not a
control -- so this one tells you exactly what it threw away, and refuses to be quiet about
it.

IMPORTANT: this reduces risk. It does not make the output provably non-personal, and this
project does not claim that it does. The artefact we consider safe to publish is a fitted
generator (tools/fit.py), not anonymised rows. This tool exists for the case where rows
must move INSIDE a boundary -- between two stores, or to a collaborator under contract --
and for showing plainly how much has to be destroyed to get even that far.
"""

import argparse, hashlib, hmac, json, os, secrets, sys
from collections import Counter, defaultdict
from datetime import datetime

# ---------------------------------------------------------------- generalisation tables

DURATION_BANDS = [(60, "under_1m"), (300, "1_5m"), (900, "5_15m"), (3600, "15_60m")]
COUNT_BANDS    = [(1, "1"), (3, "2_3"), (10, "4_10"), (50, "11_50")]
TENURE_BANDS   = [(7, "0_7d"), (30, "8_30d"), (90, "31_90d"), (365, "91_365d")]

# attribute names that are quantities we bucket rather than carry
DURATION_KEYS = {"duration_seconds", "dwell_minutes", "planned_minutes", "actual_minutes",
                 "talk_seconds", "session_seconds"}
COUNT_KEYS    = {"items", "blocks", "amount", "transitions_matched", "distinct_companions",
                 "size", "length_chars"}


def band(value, table, over):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    for edge, label in table:
        if v <= edge:
            return label
    return over


class Rekeyer:
    """HMAC re-keying under an epoch key. Destroy the key and the link is gone -- it was
    never stored, only computable."""

    def __init__(self, key: bytes):
        self.key = key
        self.seen = {}

    def __call__(self, ref: str) -> str:
        if ref not in self.seen:
            mac = hmac.new(self.key, ref.encode(), hashlib.sha256).hexdigest()[:24]
            self.seen[ref] = "e_" + mac
        return self.seen[ref]


def generalise_subject(subject, rekey, drop_tenure_exact=True):
    out = {"ref": rekey(subject["ref"])}
    if "cohort" in subject:
        out["cohort"] = subject["cohort"]          # already a coarse band by definition
    if "tenure_days" in subject and not drop_tenure_exact:
        out["tenure_days"] = subject["tenure_days"]
    elif "tenure_days" in subject:
        # exact tenure is a join key against a signup date, so it goes to a band and
        # travels in attributes rather than in the subject
        out["cohort"] = out.get("cohort", "unknown")
    return out


def generalise(o, rekey):
    """One observation in, one generalised observation out."""
    g = {
        "schema_version": o["schema_version"],
        "observation_id": "a_" + hashlib.sha256(o["observation_id"].encode()).hexdigest()[:16],
        "occurred_at": o["occurred_at"][:13] + ":00:00Z",       # hour granularity
        "source": {"platform": o["source"]["platform"], "emitter": o["source"]["emitter"]},
        "type": o["type"],
        "actor": generalise_subject(o["actor"], rekey),
    }
    if "target" in o:
        g["target"] = generalise_subject(o["target"], rekey)
    if "co_present" in o:
        g["co_present"] = [generalise_subject(c, rekey) for c in o["co_present"]]
    if "space" in o and "space_kind" in o["space"]:
        g["space"] = {"space_kind": o["space"]["space_kind"]}   # id and region dropped

    attrs = {}
    for k, v in (o.get("attributes") or {}).items():
        if k in DURATION_KEYS:
            b = band(v, DURATION_BANDS, "over_60m")
            if b: attrs[k + "_band"] = b
        elif k in COUNT_KEYS:
            b = band(v, COUNT_BANDS, "over_50")
            if b: attrs[k + "_band"] = b
        elif isinstance(v, bool):
            attrs[k] = v
        elif isinstance(v, str) and len(v) <= 16:
            attrs[k] = v                                        # short enums only
        # everything else is dropped: free text and precise numbers both identify

    tb = band(o["actor"].get("tenure_days"), TENURE_BANDS, "over_365d")
    if tb:
        attrs["actor_tenure_band"] = tb
    if attrs:
        g["attributes"] = attrs

    # session_id groups a person's activity, so it is re-keyed rather than carried
    if "session_id" in o:
        g["session_id"] = "s_" + hashlib.sha256(o["session_id"].encode()).hexdigest()[:16]

    # content_ref is removed, not re-keyed. There is no version of a content pointer that
    # belongs in a released stream.
    return g


def cell(o):
    """The unit k-anonymity is enforced over."""
    return (o["actor"].get("cohort", "unknown"),
            o["type"],
            (o.get("space") or {}).get("space_kind", "none"),
            o["occurred_at"][11:13])


def main():
    ap = argparse.ArgumentParser(description="Generalise and suppress an observation stream.")
    ap.add_argument("path")
    ap.add_argument("--out", default="anon.ndjson")
    ap.add_argument("--k", type=int, default=20,
                    help="minimum distinct participants per cell (default 20)")
    ap.add_argument("--key-file", help="epoch key to reuse; omit for a fresh random key")
    ap.add_argument("--write-key", help="write the epoch key here (destroy it to close the epoch)")
    a = ap.parse_args()

    if a.key_file:
        key = open(a.key_file, "rb").read().strip()
    else:
        key = secrets.token_bytes(32)
        if a.write_key:
            with open(a.write_key, "wb") as f:
                f.write(key)
            os.chmod(a.write_key, 0o600)

    rekey = Rekeyer(key)

    rows_in = 0
    generalised = []
    dropped_fields = Counter()
    with open(a.path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows_in += 1
            o = json.loads(line)
            if "content_ref" in o:
                dropped_fields["content_ref"] += 1
            if "space" in o and "space_id" in o["space"]:
                dropped_fields["space.space_id"] += 1
            if "recorded_at" in o:
                dropped_fields["recorded_at"] += 1
            generalised.append(generalise(o, rekey))

    # k-anonymity over cells, counting DISTINCT PARTICIPANTS and not rows: one very busy
    # child must never be able to hold a cell open by themselves.
    members = defaultdict(set)
    for o in generalised:
        members[cell(o)].add(o["actor"]["ref"])

    kept, suppressed = [], Counter()
    for o in generalised:
        c = cell(o)
        if len(members[c]) >= a.k:
            kept.append(o)
        else:
            suppressed[c[1]] += 1

    with open(a.out, "w", encoding="utf-8") as f:
        for o in kept:
            f.write(json.dumps(o, separators=(",", ":")) + "\n")

    print(f"in                : {rows_in:,} observations, {len(rekey.seen):,} participants")
    print(f"out               : {len(kept):,} observations -> {a.out}")
    print(f"suppressed        : {rows_in - len(kept):,} "
          f"({100*(rows_in-len(kept))/max(1,rows_in):.1f}%) for k<{a.k}")
    if suppressed:
        print("  by type:")
        for t, n in suppressed.most_common(10):
            print(f"    {n:>7,}  {t}")
    print("fields removed outright:")
    for k_, n in dropped_fields.most_common():
        print(f"    {n:>7,}  {k_}")
    if a.write_key:
        print(f"\nepoch key written to {a.write_key} -- DESTROY IT to close the epoch. "
              f"While it exists, this output is linkable back to the input.")
    else:
        print("\nepoch key was random and has not been written anywhere. "
              "This output cannot be linked back to its input by anyone, including us.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
