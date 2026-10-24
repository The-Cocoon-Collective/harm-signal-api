# Licensing

Two licences, one rule each. If you only read one paragraph:

> **The format is free for anyone to implement. The implementation is not free to close.**

| What | Licence | Why |
|---|---|---|
| `schema/`, `SPEC.md`, `examples/` — the standard | **Apache-2.0** | A standard nobody may implement is not a standard. Permissive, with an express patent grant, so a platform's counsel can approve adoption in an afternoon. |
| `tools/`, `analyzers/`, `reference/` — the implementation | **AGPL-3.0-or-later** | Improvements to harm detection should not disappear into a product. If you improve the analyzers and run them for other people, publish what you changed. |
| The name, the logo | **Not licensed.** See [TRADEMARKS.md](TRADEMARKS.md) | A fork may exist. It may not claim to be this. |
| Anything you contribute | You keep your copyright. See [CLA.md](CLA.md) | You own your work. We get the rights we need to keep the project relicensable and defensible. |

## Why this split and not one licence for everything

The two halves of this repository have opposite jobs.

The **schema** wants the widest possible adoption. Its whole value is that two platforms
that share nothing else can describe the same events the same way. Copyleft on a data
format is self-defeating: an emitter would have to reason about whether writing JSON in our
shape affects the licence of their own codebase, and the safe answer for their lawyer is to
not adopt it. So the schema is Apache-2.0 and that question never comes up.

The **analyzers** want the opposite. This is safety work on children's behaviour. An
analyzer that gets materially better and is then kept private has made one company's
product better and left every other child exactly where they were. AGPL is the strongest
ordinary answer to that: run a modified version as a service and you owe your users the
source.

## What AGPL does and does not get us — plainly

It is worth being honest about the limit, because we would rather say it than have someone
discover it.

AGPL's network clause triggers when users **interact with the software remotely**. A
platform that runs an analyzer internally, over its own data, as a batch job, and shows
only the resulting signals to its own staff, is arguably not triggering it at all. That is
a real gap and no licence closes it cleanly.

So the licence is one of three levers, not the only one:

1. **Licence** — AGPL keeps the code open in the cases it reaches.
2. **Trademark** — nobody may call their thing harm-signal-api, or claim conformance to it,
   without meeting the conformance tests. This is the lever that actually directs where
   forks go, and it works whether or not AGPL bites.
3. **Conformance** — a published test suite and a public list of what passes. A fork that
   will not run the tests in public is a fork nobody has a reason to trust.

A licence controls copying. A trademark and a conformance programme control **meaning**.
For a safety standard, meaning is the thing worth controlling.

## Commercial terms

If AGPL is genuinely impossible for you — and for some organisations it is a policy matter
rather than a technical one — a commercial licence to the implementation is available.
Write to help@cocoon-collective.org and say what you are building. We would rather you used
it under terms you can live with than not use it.

We do not charge researchers, schools, non-profits, or anyone working on child safety who
asks.

## SPDX

Every source file carries an `SPDX-License-Identifier` line. That is authoritative for that
file. Where a file carries none, the table above governs by directory.
