#!/usr/bin/env python3
"""
Generate a synthetic observation stream in the harm-signal-api format.

Why this exists
---------------
The real data never leaves the platform that collected it. That is not negotiable, and it
would normally mean nobody outside can work on the analysis. This closes that gap: a
contributor runs one command, gets a plausible world, and starts writing analyzers on a
Saturday without asking anyone for access to anything.

Synthetic data is genuinely good at THIS kind of data. You cannot convincingly fake a
person's sentence. You can convincingly fake an interaction graph -- degree distributions,
temporal clustering, who drifts together and who gets left out -- because those are
structural, and structure is what the analyzers are looking for.

What is planted in here on purpose
----------------------------------
Four shapes, so an analyzer has something to find and you can tell whether it works:

  ISOLATED      a participant whose group stops including them, mid-run
  ASYMMETRIC    one participant paying sustained one-way attention to one other
  NEWCOMER      arrives late with no prior edges -- the cold-start case
  WITHDRAWAL    sessions get shorter and quieter, then stop

Their refs are written to <out>.answers.json. USE THAT FOR SCORING, NOT FOR TRAINING --
an analyzer that has seen the answer key is measuring nothing.

    python3 tools/synth.py --days 30 --participants 40 --seed 7 --out synthetic.ndjson
"""

import argparse, hashlib, json, random, sys
from datetime import datetime, timedelta, timezone

SCHEMA_VERSION = "0.1.0"
PLATFORM = "synthetic"
EMITTER = "hsa-synth"
EMITTER_VERSION = "0.1.0"

SPACES = [
    ("hub.plaza",     "public"),
    ("hub.market",    "public"),
    ("hub.hall",      "shared"),
    ("hub.landing",   "transit"),
    ("island.own",    "private"),
    ("island.visit",  "shared"),
    ("arena.a",       "shared"),
]


def ref(seed: str) -> str:
    """A pseudonymous ref. Opaque, stable, and meaningless off-platform -- exactly what a
    real deployment's cipher layer should produce."""
    return "p_" + hashlib.sha256(seed.encode()).hexdigest()[:24]


class World:
    def __init__(self, n, days, seed, start):
        self.rng = random.Random(seed)
        self.days = days
        self.start = start
        self.obs = []
        self.counter = 0

        self.people = [ref(f"{seed}:{i}") for i in range(n)]
        self.tenure = {p: max(0, int(self.rng.gauss(220, 120))) for p in self.people}
        self.cohort = {p: self.rng.choice(["6-8", "6-8", "6-8", "9-12"]) for p in self.people}

        # friendship graph: a few hubs, most with 2-5 edges
        self.friends = {p: set() for p in self.people}
        for p in self.people:
            for _ in range(self.rng.choice([2, 2, 3, 3, 4, 5])):
                q = self.rng.choice(self.people)
                if q != p:
                    self.friends[p].add(q)
                    self.friends[q].add(p)

        # --- the planted shapes -------------------------------------------------
        self.isolated    = self.people[0]
        self.asym_actor  = self.people[1]
        self.asym_target = self.people[2]
        self.withdrawer  = self.people[3]
        self.newcomer    = self.people[4]

        self.tenure[self.newcomer] = 0
        self.friends[self.newcomer] = set()

    # -- emit ---------------------------------------------------------------
    def emit(self, when, otype, actor, target=None, co=None, space=None,
             attrs=None, session=None, content_ref=None):
        self.counter += 1
        o = {
            "schema_version": SCHEMA_VERSION,
            "observation_id": f"o_{self.counter:08d}",
            "occurred_at": when.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "source": {"platform": PLATFORM, "emitter": EMITTER,
                       "emitter_version": EMITTER_VERSION, "instance": "synth-1"},
            "type": otype,
            "actor": self.subject(actor),
        }
        if target:  o["target"] = self.subject(target)
        if co:      o["co_present"] = [self.subject(c) for c in co]
        if space:   o["space"] = {"space_id": space[0], "space_kind": space[1]}
        if session: o["session_id"] = session
        if attrs:   o["attributes"] = attrs
        if content_ref: o["content_ref"] = content_ref
        self.obs.append(o)

    def subject(self, p):
        s = {"ref": p, "cohort": self.cohort[p]}
        t = self.tenure.get(p)
        if t is not None:
            s["tenure_days"] = t
        return s

    # -- simulate -----------------------------------------------------------
    def run(self):
        for day in range(self.days):
            base = self.start + timedelta(days=day)
            for p in self.people:
                if p == self.newcomer and day < self.days * 0.7:
                    continue                       # arrives late
                if not self.plays_today(p, day):
                    continue
                self.session(p, base, day)
        self.obs.sort(key=lambda o: o["occurred_at"])
        return self.obs

    def plays_today(self, p, day):
        if p == self.withdrawer:
            frac = 1.0 - (day / max(1, self.days))
            return self.rng.random() < max(0.0, frac * 0.9)
        return self.rng.random() < 0.75

    def session_minutes(self, p, day):
        if p == self.withdrawer:
            return max(5, int(60 * (1.0 - day / max(1, self.days))) + self.rng.randint(-5, 5))
        return int(self.rng.gauss(55, 20))

    def companions(self, p, day):
        """Who is around. This is where the planted shapes actually bite."""
        if p == self.isolated and day > self.days * 0.4:
            return []                                   # the group stops including them
        pool = list(self.friends[p]) or [q for q in self.people if q != p]
        k = min(len(pool), self.rng.choice([0, 1, 1, 2, 2, 3]))
        return self.rng.sample(pool, k) if k else []

    def session(self, p, base, day):
        sid = f"s_{day:03d}_{p[-6:]}"
        t = base + timedelta(hours=self.rng.choice([15, 16, 17, 17, 18, 19, 20]),
                             minutes=self.rng.randint(0, 59))
        minutes = max(5, self.session_minutes(p, day))
        end = t + timedelta(minutes=minutes)

        self.emit(t, "session.begin", p, attrs={"planned_minutes": minutes}, session=sid)

        co = self.companions(p, day)
        if p == self.asym_actor and self.rng.random() < 0.85:
            co = list({*co, self.asym_target})

        cur = t
        while cur < end:
            space = self.rng.choice(SPACES)
            dwell = self.rng.randint(3, 18)
            self.emit(cur, "presence.enter", p, co=co, space=space, session=sid)

            for c in co:
                self.emit(cur + timedelta(seconds=30), "proximity.copresence", p, target=c,
                          space=space, session=sid,
                          attrs={"duration_seconds": dwell * 60})

            if p == self.asym_actor and self.asym_target in co:
                self.emit(cur + timedelta(minutes=1), "proximity.follow", p,
                          target=self.asym_target, space=space, session=sid,
                          attrs={"transitions_matched": self.rng.randint(3, 8)})
                if self.rng.random() < 0.5:
                    self.emit(cur + timedelta(minutes=2), "transfer.value", p,
                              target=self.asym_target, space=space, session=sid,
                              attrs={"amount": self.rng.randint(20, 200), "unit": "token",
                                     "reciprocated": False})

            for c in co:
                r = self.rng.random()
                if r < 0.35:
                    self.emit(cur + timedelta(minutes=self.rng.randint(1, dwell)),
                              "interaction.assist", p, target=c, space=space, session=sid)
                elif r < 0.45:
                    self.emit(cur + timedelta(minutes=self.rng.randint(1, dwell)),
                              "interaction.exchange", p, target=c, space=space, session=sid,
                              attrs={"items": self.rng.randint(1, 4)})

            if self.rng.random() < 0.30:
                self.emit(cur + timedelta(minutes=self.rng.randint(1, dwell)),
                          "artifact.create", p, space=space, session=sid,
                          attrs={"blocks": self.rng.randint(5, 400)})

            # chat is deliberately rare -- this cohort barely types, and that is the point
            chat_p = 0.05 if p != self.withdrawer else 0.05 * (1 - day / max(1, self.days))
            if self.rng.random() < chat_p:
                self.emit(cur + timedelta(minutes=self.rng.randint(1, dwell)),
                          "communication.utterance", p, space=space, session=sid, co=co,
                          attrs={"length_chars": self.rng.randint(3, 40), "language": "en"},
                          content_ref=f"c_{self.counter:08d}")

            self.emit(cur + timedelta(minutes=dwell), "presence.leave", p,
                      space=space, session=sid, attrs={"dwell_minutes": dwell})
            cur += timedelta(minutes=dwell + self.rng.randint(0, 3))

        if co and self.rng.random() < 0.25:
            self.emit(end - timedelta(minutes=1), "affiliation.form", p,
                      target=self.rng.choice(co), session=sid,
                      attrs={"size": len(co) + 1})

        self.emit(end, "session.end", p, session=sid,
                  attrs={"actual_minutes": minutes, "distinct_companions": len(set(co))})


def main():
    ap = argparse.ArgumentParser(description="Synthetic harm-signal observation stream.")
    ap.add_argument("--participants", type=int, default=40)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="synthetic.ndjson")
    a = ap.parse_args()

    start = datetime(2026, 6, 1, tzinfo=timezone.utc)
    w = World(a.participants, a.days, a.seed, start)
    obs = w.run()

    with open(a.out, "w", encoding="utf-8") as f:
        for o in obs:
            f.write(json.dumps(o, separators=(",", ":")) + "\n")

    answers = {
        "note": "Scoring only. An analyzer that has seen this is measuring nothing.",
        "seed": a.seed,
        "planted": {
            "isolation":            w.isolated,
            "asymmetric_attention": {"actor": w.asym_actor, "target": w.asym_target},
            "withdrawal":           w.withdrawer,
            "novel_contact":        w.newcomer,
        },
    }
    with open(a.out + ".answers.json", "w", encoding="utf-8") as f:
        json.dump(answers, f, indent=2)

    verbal = sum(1 for o in obs if o["type"].startswith("communication."))
    print(f"{len(obs):,} observations -> {a.out}")
    print(f"answer key            -> {a.out}.answers.json")
    print(f"non-verbal            : {100*(len(obs)-verbal)/len(obs):.1f}%  "
          f"({verbal:,} of {len(obs):,} are communication events)")


if __name__ == "__main__":
    sys.exit(main())
