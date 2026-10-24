# Changelog

## 0.2.0 — 23 September 2026

**Voice.** Added `communication.voice` to the observation vocabulary — who shared a voice
channel, with whom, where, for how long, and how much of it they were speaking. It carries
no transcript, no summary, no classification, and no pointer to a recording, and it never
will. On a platform whose children talk rather than type, this is the conversation, and
keyword moderation cannot see any of it. See SPEC.md §9.

**Repair.** Added `moderation.repair` to the vocabulary and `repair` to a signal's
`disposition`, listed before the escalating options. A safety vocabulary whose only verbs are
report and remove teaches the platform running it to punish; on a platform of six- and
seven-year-olds that is almost always the wrong first move. `repair_kind` and
`repair_accepted` also make it possible to ask whether restoration works and whether it
holds — a question the field cannot currently answer, because platforms record punishments
and not repairs. See SPEC.md §12.

**Monitoring is not moderating.** SPEC.md §9 states the difference and what each one costs:
monitoring needs no words; moderating speech requires processing speech.

**Voice is described by its rhythm, not its words.** `communication.voice` carries `turns`,
`longest_turn_seconds` and `median_gap_seconds` alongside `talk_seconds`, because the same
sentence said evenly and said in rapid fire over someone who has gone quiet are different
events, and a transcript cannot tell them apart. Two declarations, `audio_retained` and
`transcript_retained`, say what the emitting platform keeps in its own store. Neither the
audio nor the words ever enter an observation.

**Privacy pipeline.**

- `tools/anonymise.py` — epoch re-keying under a destroyable key, time and place
  generalisation, numeric banding, content removal, and k-anonymity suppression counted over
  distinct participants rather than rows.
- `tools/fit.py` — fits a generator to a real stream under a Laplace differential-privacy
  budget with a k floor, and writes publishable parameters.
- `tools/synth.py --params` — generates a world shaped like a real one from those parameters.
- `PRIVACY.md` — the three-store design, the five-year problem stated plainly, deletion,
  quarantine, and what this project will never do.

**A second analyzer.** `analyzers/structural.py` finds 76 of 80 planted shapes across twenty
seeds with no false positives, against the baseline's 40 of 80. It separates isolation from
withdrawal, which is the part that matters and the part the baseline cannot do.

**Conformance.** `tools/conformance.py` implements the four published checks — schema, no
identity, evidence, expiry. Run it and publish the output; that is the whole process.

**Licensing.** Apache-2.0 for the standard, AGPL-3.0-or-later for the implementation, a
trademark policy for the name, and contributor terms under which contributors keep their
copyright. Previously the repository declared no licence at all, which meant nobody could
legally use any of it.

**Tests and CI.** `tests/run.sh` checks every claim the README makes; GitHub Actions runs it
on every push.

**Cohorts.** The generator's cohort bands are now `6-7` and `8-10`, which is what the
platform this came from actually serves.

## 0.1.0 — 6 September 2026

Observation and signal schemas, synthetic generator with a planted answer key, reference
analyzer, scorer, validator, and the reference SQL schema.
