# Trademarks and conformance

"The Cocoon Collective", "harm-signal-api", and the associated logos are marks of
MJD Entertainment, d/b/a The Cocoon Collective(tm). The code is open. The name is not.

## What you may do without asking

- Say your software **reads, writes, or works with** the harm-signal-api format.
- Say your analyzer **is built on** harm-signal-api.
- Reproduce the name in documentation, papers, talks, comparisons and criticism.
- Fork the repository and keep the name in your fork's history, attribution and README
  provenance line. Forking is expected. It is how a standard gets stress-tested.

## What you may not do without asking

- Name your fork, product, service or package `harm-signal-api`, or a name confusable with
  it, in a way that suggests it is this project.
- State or imply that your implementation is **conformant**, **certified**, **approved** or
  **endorsed** unless it passes the published conformance tests and says which version it
  passed.
- Use the logos to brand your own product.

## Conformance

Conformance is a claim about behaviour, and behaviour can be tested. An implementation is
conformant at a schema version when:

1. Every record it emits validates against that version's schema (`tools/validate.py`).
2. It never emits a real identity, an account name, an email address, or authored content
   in any field. The schema cannot express these, and a conformant emitter does not smuggle
   them into `attributes` or `content_ref`.
3. Its signals each cite at least one observation it actually emitted, and each carries a
   rationale a non-technical reader can follow.
4. Its signals carry an expiry.

Run `python3 tools/conformance.py <your-stream.ndjson>` and publish the output. That is the
whole process. We do not charge for it and there is no committee.

## Why this exists at all

An open licence cannot stop someone shipping a weakened fork under a name parents recognise
and calling it safety. A trademark can. That is the entire purpose of this file, and it is
the only place in this project where we reserve a right rather than give one away.
