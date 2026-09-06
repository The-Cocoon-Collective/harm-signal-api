#!/usr/bin/env python3
"""
A deliberately simple reference analyzer: observations in, signals out.

This is NOT good detection. It is two crude heuristics, and it exists to show the shape of
the work and to give a contributor something that runs on the first try. Replacing it with
something better is the entire point of this repository.

    python3 tools/synth.py --out synthetic.ndjson
    python3 tools/example_analyzer.py synthetic.ndjson --out signals.ndjson
    python3 tools/validate.py signals.ndjson --schema signal
    python3 tools/score.py signals.ndjson synthetic.ndjson.answers.json

What it looks for
-----------------
ISOLATION            a participant whose distinct companions per session collapse in the
                     second half of the window relative to THEIR OWN first-half baseline.
                     Their own, not the population's -- someone who always played alone has
                     not become isolated.

ASYMMETRIC_ATTENTION one participant directing sustained one-way attention at another:
                     following, co-presence and unreciprocated transfers that do not come
                     back the other way. Interesting regardless of who the parties are,
                     which is why it is expressed structurally.
"""
import argparse, json, sys
from collections import defaultdict
from datetime import datetime

ANALYZER = {"id": "reference-heuristics", "version": "0.1.0", "method": "heuristic"}


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def load(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("observations")
    ap.add_argument("--out", default="signals.ndjson")
    a = ap.parse_args()

    obs = list(load(a.observations))
    if not obs:
        print("no observations", file=sys.stderr)
        return 1

    lo, hi = ts(obs[0]["occurred_at"]), ts(obs[-1]["occurred_at"])
    mid = lo + (hi - lo) / 2

    sess_companions = defaultdict(set)      # (ref, session) -> companion refs
    sess_half = {}
    followed = defaultdict(int)             # (a,b) -> follow count
    gave = defaultdict(int)                 # (a,b) -> unreciprocated transfers
    ev_iso = defaultdict(list)
    ev_asym = defaultdict(list)

    for o in obs:
        who = o["actor"]["ref"]
        sid = o.get("session_id")
        when = ts(o["occurred_at"])
        if sid:
            sess_half[(who, sid)] = "a" if when < mid else "b"
            # A session with nobody in it must exist as an EMPTY set, not be absent.
            # Absent reads as "no data" and the participant is skipped -- which is exactly
            # backwards, because a session with no companions is the observation that
            # matters most. This bug hid the planted isolation case on the first run.
            sess_companions.setdefault((who, sid), set())
            for c in o.get("co_present", []):
                sess_companions[(who, sid)].add(c["ref"])
            if o["type"] == "proximity.copresence" and "target" in o:
                sess_companions[(who, sid)].add(o["target"]["ref"])
            ev_iso[who].append(o["observation_id"])
        if o["type"] == "proximity.follow" and "target" in o:
            followed[(who, o["target"]["ref"])] += 1
            ev_asym[(who, o["target"]["ref"])].append(o["observation_id"])
        if o["type"] == "transfer.value" and "target" in o:
            if o.get("attributes", {}).get("reciprocated") is False:
                gave[(who, o["target"]["ref"])] += 1
                ev_asym[(who, o["target"]["ref"])].append(o["observation_id"])

    halves = defaultdict(lambda: {"a": [], "b": []})
    for (who, sid), comps in sess_companions.items():
        halves[who][sess_half[(who, sid)]].append(len(comps))

    signals, n = [], 0

    for who, h in halves.items():
        if len(h["a"]) < 3 or len(h["b"]) < 3:
            continue                                   # not enough to say anything
        first = sum(h["a"]) / len(h["a"])
        second = sum(h["b"]) / len(h["b"])
        if first < 0.8:
            continue                                   # always played alone; not a change
        drop = (first - second) / first
        if drop < 0.6:
            continue
        n += 1
        signals.append({
            "schema_version": "0.1.0",
            "signal_id": f"sig_{n:06d}",
            "generated_at": hi.isoformat().replace("+00:00", "Z"),
            "window": {"from": lo.isoformat().replace("+00:00", "Z"),
                       "to": hi.isoformat().replace("+00:00", "Z")},
            "subject": {"ref": who},
            "class": "isolation",
            "severity": "moderate" if drop < 0.85 else "high",
            "confidence": round(min(0.9, drop), 2),
            "analyzer": ANALYZER,
            "evidence": ev_iso[who][:64],
            "rationale": (f"Usually played with about {first:.1f} others per session, "
                          f"then about {second:.1f} in the second half of the period."),
            "disposition": "surface",
        })

    for (x, y), follows in followed.items():
        score = follows + 2 * gave.get((x, y), 0)
        back = followed.get((y, x), 0) + gave.get((y, x), 0)
        if score < 6 or back * 3 > score:
            continue                                   # weak, or actually mutual
        n += 1
        signals.append({
            "schema_version": "0.1.0",
            "signal_id": f"sig_{n:06d}",
            "generated_at": hi.isoformat().replace("+00:00", "Z"),
            "window": {"from": lo.isoformat().replace("+00:00", "Z"),
                       "to": hi.isoformat().replace("+00:00", "Z")},
            "subject": {"ref": x},
            "counterparties": [{"ref": y}],
            "class": "asymmetric_attention",
            "severity": "high" if score > 20 else "moderate",
            "confidence": round(min(0.9, score / 30), 2),
            "analyzer": ANALYZER,
            "evidence": ev_asym[(x, y)][:64],
            "rationale": (f"Followed or gave to the same participant {follows} time(s) "
                          f"with {back} in return."),
            "disposition": "surface",
        })

    with open(a.out, "w", encoding="utf-8") as f:
        for s in signals:
            f.write(json.dumps(s, separators=(",", ":")) + "\n")
    print(f"{len(signals)} signal(s) -> {a.out}")
    for s in signals:
        print(f"  {s['class']:<22} {s['subject']['ref'][:14]}...  conf {s['confidence']}  {s['rationale']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
