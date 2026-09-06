# Contributing

Two things are wanted, and they are quite different.

## 1. Argue with the schema

The event vocabulary came from one game, built for one age group. It is almost certainly
wrong in ways that are obvious to someone working on a different kind of platform.

Useful contributions look like: *"you have no way to express X, and here is why X matters on
a forum"*, or *"`interaction.obstruct` is doing three unrelated jobs"*, or *"this field
cannot be emitted honestly and here is what happens when people try."*

The open questions in [SPEC.md](SPEC.md) section 6 are where we already know we are weak.
Number 4 — what false-positive rate is acceptable and who decides — is the one we would most
like a real argument about.

## 2. Beat the reference analyzer

```bash
python3 tools/synth.py --days 30 --participants 40 --seed 7 --out synthetic.ndjson
python3 tools/example_analyzer.py synthetic.ndjson --out signals.ndjson
python3 tools/score.py signals.ndjson synthetic.ndjson.answers.json
```

Current baseline: **recall 2/4, three signals raised, one unexplained.** It finds the
isolated participant and the asymmetric pair; it misses the withdrawal and the newcomer.

Write something better. Any language. It must read observations conforming to
`schema/observation.schema.json` and emit signals conforming to `schema/signal.schema.json`,
and it must pass `tools/validate.py`.

**Report false positives as prominently as recall.** An analyzer that catches everything by
raising everything has not solved the problem, it has moved it onto whoever reads the
output — and in the deployment this came from, that is a parent being told something about
their child. Both numbers or neither.

Vary the seed. An analyzer tuned to seed 7 has learned seed 7.

## What we will not ask of you

- to sign anything to read this
- to handle anyone's real data, ever

If an analyzer is good enough to be worth running against a real deployment, that is done
inside the holding platform's boundary and you receive aggregate results — not access. See
[SPEC.md](SPEC.md) section 1. This is not a formality we are protecting; it is the reason the
project can exist in the open at all.

## Ground rules

- No real data in issues, pull requests or test fixtures. Not anonymised, not "just a
  sample". Use the generator.
- Nothing here is a diagnosis. Classes name **shapes**, not harms — see SPEC section 3.3 —
  and pull requests that rename `asymmetric_attention` to something accusatory will be
  declined.
- Analyzers must cite evidence and state a plain-language rationale. Both are required by the
  schema and both are load-bearing.
