#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Fit a generator to a real observation stream, under a differential-privacy budget, so the
PARAMETERS can be published and the DATA never has to be.

    python3 tools/fit.py real.ndjson --epsilon 1.0 --k 20 --out params.json
    python3 tools/synth.py --params params.json --days 30 --seed 7 --out like-real.ndjson

This is the release path described in PRIVACY.md. Every statistic below is an aggregate over
the whole population, computed with clamped sensitivity and Laplace noise, and suppressed
outright if fewer than k distinct participants contribute to it. What comes out is a small
JSON file of distributions. What never comes out is a row about a child.

The honest caveat, stated here rather than in a footnote: the accounting is a simple
per-statistic Laplace mechanism with a uniform split of the budget. It is enough to
demonstrate the shape and it has NOT been audited. Do not release real numbers under it
until someone who does this for a living has read it. That review is the outside
contribution this project most wants.
"""

import argparse, json, math, random, sys
from collections import Counter, defaultdict

CLAMP_SESSION_MIN = (5, 180)      # minutes; bounds the sensitivity of the mean
CLAMP_COMPANIONS  = (0, 8)


class Budget:
    """Uniform split of epsilon across a known number of statistics."""

    def __init__(self, epsilon, statistics, seed=None):
        self.total = epsilon
        self.each = epsilon / max(1, statistics)
        self.rng = random.Random(seed)
        self.spent = 0.0

    def laplace(self, value, sensitivity):
        scale = sensitivity / self.each
        self.spent += self.each
        u = self.rng.random() - 0.5
        noise = -scale * math.copysign(1.0, u) * math.log(1 - 2 * abs(u))
        return value + noise

    def count(self, value, sensitivity=1.0):
        return max(0.0, self.laplace(value, sensitivity))


def normalise(counter, budget, k, contributors):
    """A noisy, suppressed, normalised histogram."""
    out = {}
    for key, n in counter.items():
        if len(contributors.get(key, ())) < k:
            continue
        out[str(key)] = budget.count(n)
    total = sum(out.values())
    if total <= 0:
        return {}
    return {kk: round(v / total, 5) for kk, v in sorted(out.items())}


def main():
    ap = argparse.ArgumentParser(description="Fit synth parameters to a real stream, privately.")
    ap.add_argument("path")
    ap.add_argument("--epsilon", type=float, default=1.0)
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default="params.json")
    a = ap.parse_args()

    start_hour = Counter();      start_hour_who = defaultdict(set)
    companions = Counter();      companions_who = defaultdict(set)
    type_mix   = Counter();      type_mix_who   = defaultdict(set)
    cohorts    = Counter();      cohorts_who    = defaultdict(set)
    session_minutes = []
    people, days = set(), set()

    with open(a.path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            who = o["actor"]["ref"]
            people.add(who)
            days.add(o["occurred_at"][:10])
            type_mix[o["type"]] += 1;            type_mix_who[o["type"]].add(who)
            c = o["actor"].get("cohort")
            if c:
                cohorts[c] += 1;                 cohorts_who[c].add(who)
            if o["type"] == "session.begin":
                h = int(o["occurred_at"][11:13])
                start_hour[h] += 1;              start_hour_who[h].add(who)
            if o["type"] == "session.end":
                attrs = o.get("attributes") or {}
                m = attrs.get("actual_minutes")
                if isinstance(m, (int, float)):
                    lo, hi = CLAMP_SESSION_MIN
                    session_minutes.append(min(hi, max(lo, m)))
                d = attrs.get("distinct_companions")
                if isinstance(d, (int, float)):
                    lo, hi = CLAMP_COMPANIONS
                    d = int(min(hi, max(lo, d)))
                    companions[d] += 1;          companions_who[d].add(who)

    n_stats = 8
    b = Budget(a.epsilon, n_stats, a.seed)

    n_people = b.count(len(people))
    lo, hi = CLAMP_SESSION_MIN
    if session_minutes and len(people) >= a.k:
        mean = b.laplace(sum(session_minutes) / len(session_minutes),
                         (hi - lo) / len(session_minutes))
        var = sum((x - mean) ** 2 for x in session_minutes) / max(1, len(session_minutes))
        sd = b.laplace(math.sqrt(var), (hi - lo) / len(session_minutes))
    else:
        mean, sd = None, None

    verbal_text  = type_mix.get("communication.utterance", 0)
    verbal_voice = type_mix.get("communication.voice", 0)
    total_obs    = sum(type_mix.values())
    # Rates are per VISIT, not per observation: the generator asks "did they talk during
    # this stay in this space", so the denominator has to be the number of stays. Fitting a
    # share-of-all-events into a per-visit probability is the kind of quiet unit mismatch
    # that makes a synthetic world look nothing like the one it was fitted to.
    visits = max(1, type_mix.get("presence.enter", 0))

    params = {
        "params_version": "0.2.0",
        "fitted_from": {
            "observations": int(b.count(total_obs)),
            "participants": int(n_people),
            "days": len(days),
        },
        "privacy": {
            "mechanism": "laplace",
            "epsilon_total": a.epsilon,
            "epsilon_per_statistic": round(b.each, 5),
            "statistics": n_stats,
            "k_floor": a.k,
            "audited": False,
            "note": "Every figure below carries calibrated noise. Do not read any single "
                    "number as exact -- that is the point of it.",
        },
        "start_hour":  normalise(start_hour, b, a.k, start_hour_who),
        "companions":  normalise(companions, b, a.k, companions_who),
        "cohorts":     normalise(cohorts,    b, a.k, cohorts_who),
        "type_mix":    normalise(type_mix,   b, a.k, type_mix_who),
        "session_minutes": (None if mean is None
                            else {"mean": round(max(lo, mean), 2),
                                  "sd": round(max(1.0, sd), 2)}),
        "rates_are": "per visit to a space (presence.enter)",
        "text_rate":  round(min(1.0, verbal_text / visits), 6),
        "voice_rate": round(min(1.0, verbal_voice / visits), 6),
    }

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)

    print(f"fitted from {total_obs:,} observations, {len(people):,} participants, "
          f"{len(days)} days")
    print(f"epsilon {a.epsilon} across {n_stats} statistics "
          f"({b.each:.4f} each), k floor {a.k}")
    print(f"start-hour buckets kept {len(params['start_hour'])}/{len(start_hour)}, "
          f"companion buckets kept {len(params['companions'])}/{len(companions)}, "
          f"types kept {len(params['type_mix'])}/{len(type_mix)}")
    print(f"-> {a.out}   (this file is publishable; the input is not)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
