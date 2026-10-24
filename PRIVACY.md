# Privacy, anonymisation, and the five-year problem

This file is the argument, not the boilerplate. The code that implements it is
[`tools/anonymise.py`](tools/anonymise.py) and [`tools/fit.py`](tools/fit.py).

---

## The problem, stated honestly

A `ref` in this schema is **pseudonymous**. Pseudonymous is not anonymous. It is personal
data in every regime that matters, it stays personal data forever, and calling it anonymous
because it looks like a hash is the single most common lie told about datasets of this kind.

That is uncomfortable here, because the most valuable thing this project could ever produce
is exactly the thing that makes the problem worse: **a five-year record of how children
actually behave online.** Not opinions about it. Not a survey. The record. Nobody has one
that is both real and shareable, which is why so much child-safety design is argued from
anecdote.

And behavioural trajectories are not hard to re-identify. They are *easier* than names. A
name is shared by thousands of people; a five-year pattern of when you play, where you go
first, and who you follow is shared by nobody. A long per-person behavioural history is
among the most identifying artefacts a platform can hold, and the longer it is, the more
identifying it gets. **Length is the risk. Length is also the value.** There is no version
of this where those two things are separated by being careful.

So we do not try to make the history anonymous. We make sure the thing we *publish* is not
the history.

---

## Three stores, one direction of travel

```
  operational            longitudinal                    research release
  (platform-held)        (platform-held)                 (public)
  pseudonymous           pseudonymous                    not personal data at all
  short retention        long retention, minimised       DP statistics + a fitted generator
  feeds live signals     feeds internal research         feeds everyone else
        │                        │                                │
        └──── nothing leaves ────┴──── nothing row-level leaves ──┘
```

**1. Operational.** What the analyzers run against today. Days to weeks. Never leaves.

**2. Longitudinal.** Where a five-year picture can exist. Still pseudonymous, still personal
data, still subject to a parent's access and deletion rights, still never leaves the
platform. We do not describe it as anonymous, to anyone, ever. It is minimised hard on the
way in: no content, no free text, generalised times, generalised places.

**3. Research release.** This is the part that is allowed to be public, and it contains no
rows about anybody. Two artefacts, and only these two:

- **Differentially private cohort statistics.** Counts, distributions, transition matrices —
  each computed with calibrated noise under a published privacy budget, and each suppressed
  unless it rests on at least *k* distinct participants.
- **A fitted generator.** Parameters estimated from the real stream under the same budget,
  shipped as a small JSON file that [`tools/synth.py`](tools/synth.py) consumes. Anyone can
  then generate an unlimited stream that behaves statistically like a real children's
  platform and describes no child who has ever existed.

> **We publish the physics, not the people.**

That sentence is the whole design. A researcher who wants to know whether exclusion has a
detectable shape does not need a real child's record. They need a world with the same
structure, and an answer key. This repository already produces one; fitting it to real
distributions is what makes it worth trusting.

---

## Why the generator is the release format, and not "anonymised rows"

The usual approach is to release rows with the identifiers stripped and some jitter added.
It fails in a predictable way: the structure that makes the data useful is the structure
that makes it re-identifiable, so every increment of genuine privacy costs an increment of
research value, and the released set ends up too weak to publish a paper from and still too
strong to defend in a DPIA.

Fitting a generator moves the trade-off somewhere better. The **parameters** are aggregates
over the whole population, so noise can be added where it costs least; the **rows** are
generated, so there is no individual to re-identify, and no amount of auxiliary data links a
generated participant to a real one, because there is no link to find. The failure mode
becomes "the generated world is subtly unlike the real one", which is a *scientific* problem
that can be measured, argued about in public, and fixed — rather than a *privacy* problem
that can only be discovered by someone being harmed.

---

## Epochs, and the key we destroy

Refs are not permanent. They are derived per **epoch**:

```
ref_epoch = "p_" + HMAC(epoch_key, participant_id)[:24]
```

When an epoch closes, its key is destroyed. After that, nobody — including us — can link a
participant across the boundary, because the link was never stored; it was computable, and
now it is not.

Epoch length is the dial where privacy and research trade against each other, and we would
rather expose the dial than pretend there is a setting that costs nothing:

| Epoch | What you can study | What you are holding |
|---|---|---|
| 1 day | today's session | almost nothing |
| 30 days | a term's worth of group formation | a month-long behavioural profile |
| 5 years | development over childhood | the most identifying artefact in the building |

Default: **90 days** operationally. Anything longer is a deliberate, documented, consented
decision taken inside the platform boundary, never a default and never inherited by a
release.

---

## Deletion has to actually work

A parent asks for their child's record to be deleted. Three things have to happen, and the
third is the one projects forget:

1. Observations for that participant are deleted from both platform stores.
2. Signals citing them are deleted — which is possible only because every signal carries the
   `observation_id` values it rests on. A signal that cannot name its evidence cannot be
   unwound, which is a second reason the evidence field is mandatory.
3. Nothing already published can be recalled. So a release must never be able to contain a
   child who might later be deleted in a way that matters. Two rules handle it:
   - **Quarantine.** No release draws on data more recent than 90 days.
   - **Floor.** No released statistic rests on fewer than *k* distinct participants
     (default `k = 20`), so no individual's presence or absence changes a published number
     in a way an observer could detect.

---

## What the anonymiser actually does

[`tools/anonymise.py`](tools/anonymise.py), in order:

1. **Re-keys** every `ref` under a fresh epoch key.
2. **Generalises time** — `occurred_at` to the hour; `recorded_at` dropped.
3. **Generalises place** — `space_id` and `region` dropped, `space_kind` kept.
4. **Drops content entirely** — `content_ref` removed. Not re-keyed. Removed.
5. **Buckets numeric attributes** — durations, amounts and counts to coarse bands.
6. **Coarsens tenure** — exact days to a band.
7. **Suppresses small cells** — any `(cohort, type, space_kind, hour-of-day)` cell with
   fewer than *k* distinct participants is dropped, and the count of what was dropped is
   reported rather than hidden.
8. **Reports.** It prints what it removed and what survived, because an anonymiser whose
   output you cannot inspect is a claim, not a control.

It is deliberately lossy and the losses are deliberately visible. If the output is still
useful, the pipeline worked. If it is not, that is the honest answer about what could safely
have been shared — and the generator route exists precisely because the honest answer is
usually "less than you hoped".

---

## What we will not do

- We will not sell this data, in any form, ever. Not aggregated, not "de-identified", not
  through an intermediary.
- We will not publish row-level records about children, however processed.
- We will not describe pseudonymous data as anonymous.
- We will not train a model on children's behaviour and then ship the model as though the
  training data were gone. A model can memorise. Anything released as a model gets the same
  privacy budget and the same floor as anything else released, or it is not released.
- We will not let a research collaboration become a back door to the store. Collaborators
  get the generator, the statistics, and an answer key. If an analyzer needs the real
  stream, the analyzer comes to the data and the results leave; the data does not move.

---

## Status

This file describes the design. `anonymise.py` and `fit.py` implement it against synthetic
input today. The differential-privacy accounting in `fit.py` is a simple Laplace mechanism
with a per-statistic budget — adequate to demonstrate the shape, and explicitly **not**
audited. Before a single real number is released under it, that accounting needs review by
someone who does this for a living. We would like that to be one of the first outside
contributions this project receives.
