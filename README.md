# harm-signal-api

**An open schema for behavioural harm signals — and a synthetic dataset so you can work on
them without anyone handing you real data about real people.**

Status: **draft 0.2.0.** The schemas are usable, the privacy pipeline runs, and the
reference analyzer is deliberately weak so there is something to beat. The interesting work
has not been done yet.

[Licensing](LICENSING.md) · [Privacy](PRIVACY.md) · [Spec](SPEC.md) ·
[Implementation](IMPLEMENTATION.md) · [Contributing](CONTRIBUTING.md)

---

## The idea in one paragraph

Platforms that want to keep people safe all hit the same wall. The data that would let you
detect harm is the data you must not hand to anyone. So safety analysis gets done by whoever
happens to hold the data, in private, once, and nobody else can check it or improve it.

This repository proposes a different split. **Observations** — the record of what happened —
stay with the platform that collected them, forever. **The format is public. The analysis is
public. The raw record never is.** Anyone can write, test and publish an analyzer against a
synthetic stream in the same format, and a platform can then run that analyzer against its
own data without the author ever seeing a row of it.

## Why the schema is not about children, even though we built it for a children's platform

We built this for [The Cocoon Collective](https://github.com/The-Cocoon-Collective), a
Minecraft platform for young children. But nothing in the schema knows that.

The shapes that matter — someone being frozen out of a group, one person paying sustained
one-way attention to another, a newcomer with no connections, a participant going quiet —
are not childhood shapes. They are **interaction shapes**, and they look much the same in a
classroom app, a forum, a game or a workplace. So the vocabulary is deliberately
domain-neutral, and a platform describes itself through a profile rather than through the
schema.

If you have a harm-detection problem and a stream of interactions, this should fit.

## ⭐ The part people get wrong: it is mostly not about what anyone says

Text is the easy part. It is also the part everybody already does, and on the platform this
came from it is nearly useless. The participants are **six and seven years old**. They cannot
type fast enough to say much at all. In-game voice is the channel they will use once it is
built — it is the next piece of that platform's foundation and it is not finished — and
voice is the one channel a keyword filter cannot read at all. Meanwhile they play together,
follow each other around, trade, build, include and exclude. That is the stream, and it is
there today.

Run the generator and look at the ratio:

```
24,165 observations
structural      : 90.7%   who did what, with whom, where, in what order
voice presence  :  8.5%   who was in a channel, with whom, how long, at what pace
typed text      :  0.8%   (204 of 24,165) the only part keyword moderation can see
```

**That is the design claim.** Content moderation can see under one percent of the record.
A platform whose children speak rather than type is, if text is all it reads, moderating
almost nothing. This schema is built for the other ninety-nine percent.

`communication.voice` carries *who, with whom, where, how long, and in what rhythm* — turns,
gaps, and whether one participant held the floor. **It never carries the words.** A platform
may hold a transcript in its own store and say so in `transcript_retained`; the words do not
enter this schema, and no analyzer written against it reads them.

(Those proportions come from the generator, which is a model of a children's platform, not a
measurement of one. Fitting them to a real stream is what `tools/fit.py` is for, and no such
fit has been published.)

It also means content never has to be in the stream at all. An observation carries a
`content_ref`, an opaque pointer, and never the words themselves.

---

## Try it — three commands, no access to anything required

```bash
pip install -r requirements.txt
python3 tools/synth.py --days 30 --participants 40 --seed 7 --out synthetic.ndjson
python3 analyzers/structural.py synthetic.ndjson --out signals.ndjson
python3 tools/score.py signals.ndjson synthetic.ndjson.answers.json
```

The generator plants four shapes and writes an answer key.

| analyzer | what it is | shapes found | false positives |
|---|---|---|---|
| `tools/example_analyzer.py` | two crude heuristics, kept as the baseline | **40 / 80** | 1 |
| `analyzers/structural.py` | the first serious attempt | **76 / 80** | **0** |

*Twenty seeds, thirty days, forty participants, four planted shapes each. Reproduce it with
`tests/run.sh`, or argue with it — the numbers are the point of publishing them.*

The four shapes are isolation, withdrawal, asymmetric attention and novel contact. The hard
part is not finding them; it is **telling isolation and withdrawal apart**, because in a
weekly engagement total they look identical and they mean opposite things. One is something
being done to a child. The other is a child doing less. A detector that reports "engagement
down" for both has not helped anybody — it has sent a parent the wrong conversation.

`analyzers/structural.py` is written to be beaten in turn. Beat it.

---

## Privacy: the five-year problem, and what we publish instead of data

The most valuable thing this project could produce is a long, real record of how children
actually behave online — and that is exactly the thing that cannot be published. A `ref` is
pseudonymous, pseudonymous is not anonymous, and a five-year behavioural trajectory is more
identifying than a name, not less. Length is the value and length is the risk, and no amount
of care separates them.

So we do not publish the record. We publish **the physics, not the people**:

```bash
python3 tools/anonymise.py real.ndjson --out anon.ndjson --k 20   # inside the boundary only
python3 tools/fit.py real.ndjson --epsilon 1.0 --k 20 --out params.json
python3 tools/synth.py --params params.json --days 30 --out like-real.ndjson
```

`fit.py` estimates the distributions of a real stream under a differential-privacy budget
and writes a small JSON file. `synth.py` then generates an unlimited world that behaves like
the real one and describes no child who has ever existed. The parameters are publishable.
The input never was.

[PRIVACY.md](PRIVACY.md) has the full design: three stores, epoch keys that get destroyed,
k-anonymity floors, quarantine before release, and a plain statement of what we will never
do. The differential-privacy accounting is a simple Laplace mechanism and is **not audited**.
Getting that reviewed by someone who does it for a living is the outside contribution this
project most wants.

---

## The two record types, and why they must never be one

| | **Observation** | **Signal** |
|---|---|---|
| is | a fact | an opinion |
| says | "A and B were both in the hall for 90 seconds" | "A may be being excluded" |
| written by | the platform | an analyzer |
| leaves the platform | **never** | yes, to a reporting layer |
| carries | a pseudonymous ref, a type, a time, a place | evidence, confidence, a plain-English reason |

Collapsing these two is the mistake this schema exists to prevent. Once a judgement is
stored next to the fact that produced it, you can no longer re-derive one without the other,
you cannot swap the analyzer without rewriting history, and you cannot show someone the
evidence separately from the conclusion.

**Every signal cites the observation ids it rests on and states its reasoning in a sentence
a non-technical person can read.** A signal that cannot be explained plainly should not be
raised. It is also what makes deletion work: when a parent asks for a child's record to be
removed, the signals derived from it can be found and removed too, because each one names
its evidence.

## What is deliberately absent

- **No identity.** A subject is a `ref` — pseudonymous, stable within a platform, meaningless
  outside it. There is no field for a name, an account, an email or an address. **The schema
  cannot express a real identity, so an emitter cannot leak one through it by accident.**
- **No content.** Authored text is referenced, never carried. Speech is described by its
  shape — turns, pace, who held the floor — and never by its words. Whether a platform keeps a
  transcript of its own is a fact it must declare, not a thing this schema can hold.
- **No authority.** A signal's `disposition` is advisory. Nothing consuming this schema is
  granted power over a participant. The platform decides, and remains accountable.
- **No permanence.** Signals carry `expires_at`. A conclusion with no expiry becomes a
  permanent mark on a person, and that is a failure mode, not a feature.

---

## Repository layout

```
schema/observation.schema.json   what happened          (JSON Schema 2020-12)
schema/signal.schema.json        what an analyzer concluded
tools/synth.py                   synthetic stream + answer key; --params for a fitted world
tools/fit.py                     private fit of a real stream -> publishable parameters
tools/anonymise.py               epoch re-keying, generalisation, k-anonymity suppression
tools/example_analyzer.py        the weak baseline, kept honest and kept slow
tools/score.py                   scores signals against the answer key
tools/validate.py                schema validation, CI-friendly exit codes
tools/conformance.py             the four conformance checks; run it, publish the output
analyzers/structural.py          the current best analyzer
tests/run.sh                     every claim in this README, checked in one command
examples/                        a sample stream you can read
SPEC.md                          the reasoning, the event vocabulary, open questions
PRIVACY.md                       anonymisation, retention, and what may be published
IMPLEMENTATION.md                the tables, what each is for, how to adopt it
LICENSING.md                     two licences and why they differ
reference/watcher-schema.sql     the 9 tables / 28 types, ready to run
```

## The tables exist. You can create them today.

[`reference/watcher-schema.sql`](reference/watcher-schema.sql) is the physical schema —
**nine tables covering all twenty-eight observation types**, MySQL 8 / MariaDB, ready to run
against an empty database. It is generated from the reference emitter's own code, so it
cannot drift from what that plugin actually builds.

You do not have to design a database to start. You have to collect these data points.

[IMPLEMENTATION.md](IMPLEMENTATION.md) walks through what each table is for, the four rows
that matter most, and the one column that cannot be backfilled.

## Where this fits

```
a platform          its own store            this repo              a reporting layer
(emits)        →    (private, always)   →    (analysis, public)  →  e.g. parent-dashboard
observations        the raw record           signals                what a person sees
```

Written against [`parent-dashboard`](https://github.com/The-Cocoon-Collective/parent-dashboard),
which consumes signals — *"activity summaries, not keystroke logs."*

## Licence

| | |
|---|---|
| `schema/`, `SPEC.md`, `examples/` | **Apache-2.0** — implement it anywhere, including in closed software |
| `tools/`, `analyzers/`, `reference/` | **AGPL-3.0-or-later** — improve the detection and the improvement stays open |
| the name and the logo | a trademark; conformance is a test you run, not a badge we sell |
| your contribution | **you keep your copyright** |

The reasoning, including an honest account of what AGPL does *not* reach, is in
[LICENSING.md](LICENSING.md).

## Contributing

Open questions, the ones we would most like help with, and the honest list of what is
missing are in [SPEC.md](SPEC.md) and [CONTRIBUTING.md](CONTRIBUTING.md). Short version:
**the schema wants argument, and the analyzers want beating.**

One rule with no exceptions: **never open a pull request containing real data.** Use
`tools/synth.py`.

We will not ask you to sign anything to look at this, and we will never ask you to handle
anyone's real data.
