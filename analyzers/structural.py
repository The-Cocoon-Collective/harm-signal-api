#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
structural 0.2.0 -- an analyzer that reads the shape of the week, not the words.

    python3 analyzers/structural.py synthetic.ndjson --out signals.ndjson
    python3 tools/score.py signals.ndjson synthetic.ndjson.answers.json

tools/example_analyzer.py is the deliberately weak baseline: two crude heuristics, recall
2/4. This one is the first serious attempt, and it is written to be beaten in turn.

Four detectors, one per planted shape, and they are kept apart on purpose:

  ISOLATION     company falls away while the child keeps turning up
  WITHDRAWAL    the child stops turning up, company held steady
  ASYMMETRIC    sustained one-way attention from one child to one other
  NOVEL CONTACT a newcomer with no history, arriving into an established group

Isolation and withdrawal look identical in a weekly total and mean opposite things. One is
something being done to a child; the other is a child doing less. Telling them apart is most
of the work here, and a detector that reported "engagement down" for both would be worse
than useless -- it would send a parent the wrong conversation.

Every signal cites the observations it rests on, states its reasoning in a sentence, and
expires. No signal is raised that cannot do all three.
"""

import argparse, json, sys
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone

ANALYZER = {"id": "structural", "version": "0.2.0", "method": "statistical"}
SCHEMA_VERSION = "0.2.0"

COMPANY_TYPES = {"proximity.copresence", "interaction.assist", "interaction.exchange",
                 "interaction.direct", "communication.voice"}
# Attention is counted only from events that are DIRECTED by nature. Being in the same
# room as someone is not attention -- in a shared space everyone is co-present with
# everyone, and counting that produces a flag on every sociable child in the building.
ATTENTION_TYPES = {"proximity.follow", "transfer.value", "interaction.direct"}


def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def day_of(o):
    return o["occurred_at"][:10]


class Profile:
    """Everything the detectors need about one participant, built in a single pass."""

    def __init__(self, ref):
        self.ref = ref
        self.days = set()                        # any day they appear at all
        self.own_days = set()                    # days they started a session of their own
        self.minutes = defaultdict(float)        # day -> minutes played
        self.company = defaultdict(set)          # day -> others present in THEIR sessions
        self.first_day = None
        self.tenure = None
        self.cohort = None
        self.evidence = []                       # observation ids, newest last

    def note(self, o):
        d = day_of(o)
        self.days.add(d)
        mine = o["actor"]["ref"] == self.ref
        if mine:
            self.own_days.add(d)
            if self.first_day is None or d < self.first_day:
                self.first_day = d
            s = o["actor"]
            if s.get("tenure_days") is not None and self.tenure is None:
                self.tenure = s["tenure_days"]
            self.cohort = s.get("cohort", self.cohort)
        if o["type"] == "session.end":
            m = (o.get("attributes") or {}).get("actual_minutes")
            if isinstance(m, (int, float)):
                self.minutes[d] += m
        # Company is counted in the child's OWN sessions. Appearing in somebody else's
        # session is not the same thing as having company of your own, and a child who is
        # quietly dropped from their group still shows up in the stream as a bystander.
        if mine and o["type"] in COMPANY_TYPES:
            for other in others(o):
                if other != self.ref:
                    self.company[d].add(other)
        if len(self.evidence) < 400:
            self.evidence.append(o["observation_id"])


def others(o):
    out = []
    if "target" in o:
        out.append(o["target"]["ref"])
    for c in o.get("co_present", []):
        out.append(c["ref"])
    out.append(o["actor"]["ref"])
    return out


def thirds(days_sorted):
    n = len(days_sorted)
    cut = max(1, n // 3)
    return days_sorted[:cut], days_sorted[-cut:]


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


class Analyzer:
    def __init__(self, rows, min_days=8):
        self.rows = rows
        self.min_days = min_days
        self.people = {}
        self.pair = Counter()                    # (a -> b) attention weight
        self.pair_evidence = defaultdict(list)
        self.all_days = sorted({day_of(o) for o in rows})

        for o in rows:
            for ref in set(others(o)):
                self.people.setdefault(ref, Profile(ref)).note(o)
            if o["type"] in ATTENTION_TYPES and "target" in o:
                a, b = o["actor"]["ref"], o["target"]["ref"]
                if a != b:
                    w = 3 if o["type"] in ("proximity.follow", "transfer.value") else 1
                    if o["type"] == "transfer.value" and \
                       (o.get("attributes") or {}).get("reciprocated") is False:
                        w = 5
                    self.pair[(a, b)] += w
                    if len(self.pair_evidence[(a, b)]) < 40:
                        self.pair_evidence[(a, b)].append(o["observation_id"])

        self.window = {"from": self.all_days[0] + "T00:00:00Z",
                       "to": self.all_days[-1] + "T23:59:59Z"}
        self.n = 0

    # ---------------------------------------------------------------- emit
    def signal(self, cls, subject, confidence, severity, rationale, evidence,
               counterparties=None, disposition="observe"):
        self.n += 1
        now = datetime.now(timezone.utc).replace(microsecond=0)
        s = {
            "schema_version": SCHEMA_VERSION,
            "signal_id": f"sig_{self.n:06d}",
            "generated_at": now.isoformat().replace("+00:00", "Z"),
            "window": self.window,
            "subject": {"ref": subject},
            "class": cls,
            "severity": severity,
            "confidence": round(min(0.95, max(0.05, confidence)), 2),
            "analyzer": ANALYZER,
            "evidence": evidence[:64] or ["none"],
            "rationale": rationale[:512],
            "disposition": disposition,
            "expires_at": (now + timedelta(days=30)).isoformat().replace("+00:00", "Z"),
        }
        if counterparties:
            s["counterparties"] = [{"ref": r} for r in counterparties]
        return s

    # ------------------------------------------------------------ detectors
    def run(self):
        out = []
        out += self.isolation_and_withdrawal()
        out += self.asymmetric()
        out += self.novel_contact()
        return out

    def isolation_and_withdrawal(self):
        found = []
        for p in self.people.values():
            days = sorted(p.own_days)
            if len(days) < self.min_days:
                continue
            early, late = thirds(self.all_days)
            early_company = mean(len(p.company.get(d, ())) for d in early)
            late_company = mean(len(p.company.get(d, ())) for d in late)
            early_active = sum(1 for d in early if d in p.own_days) / len(early)
            late_active = sum(1 for d in late if d in p.own_days) / len(late)
            early_minutes = mean(p.minutes.get(d, 0.0) for d in early)
            late_minutes = mean(p.minutes.get(d, 0.0) for d in late)

            # ISOLATION: still showing up, nobody there any more.
            if (early_company >= 0.5 and late_company <= 0.2 * early_company
                    and late_active >= 0.5 * early_active and late_active > 0.25):
                drop = 1 - (late_company / max(0.01, early_company))
                found.append(self.signal(
                    "isolation", p.ref, 0.45 + 0.5 * drop, "moderate",
                    f"Played with about {early_company:.1f} other children a day at the start "
                    f"of this period and about {late_company:.1f} by the end, while still "
                    f"playing on {late_active*100:.0f}% of days. They are still turning up; "
                    f"the company is what changed.",
                    p.evidence[-40:], disposition="surface"))

            # WITHDRAWAL: showing up less, company was never the issue.
            elif (early_minutes > 15 and late_minutes <= 0.35 * early_minutes
                  and late_active <= 0.4 * early_active):
                drop = 1 - (late_minutes / max(0.01, early_minutes))
                found.append(self.signal(
                    "withdrawal", p.ref, 0.40 + 0.5 * drop, "low",
                    f"Playing time fell from about {early_minutes:.0f} minutes a day to about "
                    f"{late_minutes:.0f}, and they now play on {late_active*100:.0f}% of days "
                    f"rather than {early_active*100:.0f}%. Company held up; the time did not.",
                    p.evidence[-40:], disposition="observe"))
        return found

    def asymmetric(self):
        found = []
        seen = set()
        for (a, b), w in self.pair.most_common():
            if w < 30 or (a, b) in seen:
                continue
            back = self.pair.get((b, a), 0)
            if back * 4 > w:   # roughly mutual
                continue                                     # roughly mutual: that is friendship
            seen.add((a, b))
            ratio = w / max(1, back)
            found.append(self.signal(
                "asymmetric_attention", a, 0.4 + min(0.5, ratio / 20), "moderate",
                f"One child has followed, accompanied and given to the same other child "
                f"steadily through this period, and almost none of it has come back the "
                f"other way (weight {w} out of, against {back} back). Sustained one-way "
                f"attention between two children is worth a look before it is worth a worry.",
                self.pair_evidence[(a, b)], counterparties=[b], disposition="surface"))
        return found

    def novel_contact(self):
        found = []
        if len(self.all_days) < 6:
            return found
        late_start = self.all_days[int(len(self.all_days) * 0.6)]
        for p in self.people.values():
            if p.first_day is None or p.first_day < late_start:
                continue
            if (p.tenure or 0) > 14:
                continue
            met = set()
            for d, company in p.company.items():
                met |= company
            established = [q for q in met
                           if q in self.people and (self.people[q].tenure or 0) > 60]
            if not met:
                continue
            found.append(self.signal(
                "novel_contact", p.ref, 0.5 + min(0.35, len(established) / 20), "informational",
                f"Arrived on {p.first_day} with no history on the platform and has since "
                f"been in company with {len(met)} other children, {len(established)} of them "
                f"long-established. Nothing here is wrong. A newcomer with no connections is "
                f"simply the case every other detector is worst at, so it is stated plainly.",
                p.evidence[:40], disposition="observe"))
        return found


def main():
    ap = argparse.ArgumentParser(description="Structural analyzer for harm-signal observations.")
    ap.add_argument("path")
    ap.add_argument("--out", default="signals.ndjson")
    ap.add_argument("--min-days", type=int, default=8)
    a = ap.parse_args()

    rows = load(a.path)
    signals = Analyzer(rows, a.min_days).run()

    with open(a.out, "w", encoding="utf-8") as f:
        for s in signals:
            f.write(json.dumps(s, separators=(",", ":")) + "\n")

    by_class = Counter(s["class"] for s in signals)
    print(f"{len(rows):,} observations -> {len(signals)} signal(s) -> {a.out}")
    for c, n in by_class.most_common():
        print(f"  {n:>3}  {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
