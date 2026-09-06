# harm-signal-api — specification, draft 0.1.0

Reasoning, the vocabulary, and what is still open. The normative artifacts are the two JSON
Schema files; where this document and a schema disagree, the schema wins.

---

## 1. The problem this shape solves

Harm detection needs the data that must not be shared. That single fact produces every
pathology in the field: analysis done once, in private, by whoever holds the data; no
external review; no comparison between platforms; and a small number of large companies as
the only parties who can even attempt it.

The split proposed here:

| | stays private | is public |
|---|---|---|
| the raw record of what people did | always | never |
| the **format** of that record | | yes |
| the **analysis** performed on it | | yes |
| a **synthetic** stream in that format | | yes |
| the **signals** produced | to the platform's own reporting layer | schema is public |

An analyzer is developed and scored against synthetic data by anyone, then executed against
real data **inside the holding platform's boundary**, with only aggregate signals coming
back out. The author never sees a row. This is the *code-to-data* pattern from research data
governance, and it is what makes outside contribution possible at all here.

## 2. Observations

An observation is a fact with a time, an actor, a type, and usually a place. It carries no
interpretation. See `schema/observation.schema.json`.

### 2.1 Subjects are pseudonymous by construction

```json
{ "ref": "p_8d8ea3758174b90cba327262", "cohort": "6-8", "tenure_days": 412 }
```

`ref` is opaque and stable within one platform. Resolving it to a person requires a mapping
the platform holds and never publishes.

**The schema has no field for a real identity — no name, no account id, no address.** This is
the load-bearing decision in the whole design. A rule that says "do not put names in here"
gets broken by a tired engineer at some point. A schema that has nowhere to put a name does
not.

`cohort` and `tenure_days` exist because they are legitimately conditioning variables: a
newcomer with no edges behaves differently from an established participant, and an analyzer
that cannot see that will call every new arrival an anomaly. Keep `cohort` coarse.

### 2.2 Co-presence is recorded, never reconstructed

`co_present` lists who else was in scope **at the moment of writing**.

This is not convenience. Two independent streams joined on timestamps afterwards produce
guesses, because presence has duration and events have instants, and "in scope" is a
platform-specific judgement the platform is uniquely able to make. **If the emitter does not
write it down, the information does not exist.**

### 2.3 Content is referenced, never carried

`communication.utterance` carries `content_ref`, an opaque pointer, plus safe derived
attributes (`length_chars`, `language`). The words stay in the platform's own store under
its own controls.

An analyzer that genuinely needs text is asking to run inside the boundary. That is a
different and much heavier request, and the schema makes it visible rather than easy.

### 2.4 The event vocabulary

Twenty-six types in nine families. Overwhelmingly non-verbal, on purpose.

| family | types | what it captures |
|---|---|---|
| `session` | `begin` `end` | when someone was present at all, and for how long |
| `presence` | `enter` `leave` `dwell` | where they went |
| `proximity` | `copresence` `follow` `avoid` | who they were near, who they tracked, who they steered clear of |
| `interaction` | `direct` `assist` `obstruct` `exchange` | what they did to or with each other |
| `affiliation` | `form` `join` `leave` `remove` `invite` `decline` | groups forming, and people being put out of them |
| `artifact` | `create` `modify` `destroy` | what they made, and what got broken |
| `transfer` | `value` | economy, gifts, unreciprocated giving |
| `communication` | `utterance` `direct` | that something was said — not what |
| `moderation` | `action` `report` | the platform's own interventions, so an analyzer can see them |

`proximity.avoid` and `affiliation.remove` are the two most easily overlooked and among the
most informative. **Absence is a signal**, and absence is only visible if somebody writes it
down.

`attributes` is an open object for type-specific numbers, enums, durations and counts. It
must never carry free text authored by a person — that is what `content_ref` is for.

## 3. Signals

See `schema/signal.schema.json`. Required: a window, a subject, a class, a confidence, the
analyzer's identity and version, at least one cited observation, and a plain-language
rationale.

### 3.1 Severity and confidence are separate

Severity is *how much it matters if true*; confidence is *how sure we are*. Collapsing them
into one number hides the most dangerous shape in the field: **high severity, low
confidence** — the accusation that might be nothing. A consumer must be able to threshold on
each.

### 3.2 Rationale is mandatory and must be plain

> *"Usually played with about 1.7 others per session, then about 0.0 in the second half of
> the period."*

Written for the person who will read it. If a conclusion cannot be stated plainly it should
not be raised, because the alternative is an adult acting on a number they cannot
interrogate.

### 3.3 Classes name shapes, not harms

`isolation`, `withdrawal`, `exclusion`, `asymmetric_attention`, `novel_contact`,
`contact_escalation`, `boundary_probe`, `reciprocity_imbalance`, `value_imbalance`,
`schedule_anomaly`, `behavioural_drift`, `cohort_atypical`, `content_flag`,
`off_platform_indicator`.

None of these names a harm. `asymmetric_attention` is not "grooming" — it is a structure that
can be measured and checked, and that is sometimes entirely innocent. Naming the shape keeps
the analyzer honest and keeps the human judgement where it belongs.

### 3.4 Signals expire, and carry no authority

`expires_at` exists so a conclusion does not become a permanent mark. `disposition` is
advisory; the platform acts and remains accountable.

### 3.5 Counterparties are a disclosure decision

Naming a second participant in a signal about a first is a real decision, particularly when
the reporting layer shows it to a guardian. The field exists so that decision is explicit
rather than an accident of a join.

## 4. Emitting

Any platform, any plugin, any number of them. `source.platform` and `source.emitter` mean one
store can hold several producers and an analyzer can weight them differently.

**A contract gets many producers for free; a shared library gets one.** That is the argument
for a schema rather than an SDK, and it is why an unrelated plugin can start contributing to
the same stream without knowing anything about the others.

Emitters should validate in CI (`tools/validate.py` exits non-zero on failure). An emitter
that breaks the contract should fail its own build, not a consumer's dashboard at 2am.

## 5. Synthetic data — what it is good for and where it stops

`tools/synth.py` produces a plausible interaction graph with four planted shapes and an
answer key.

**Genuinely works:** writing and testing analyzers, reproducibility, working out which fields
you need before asking anyone for anything.

**Does not work:** validating that a detector actually detects real harm. The research
caveat is that synthetic data fails for nonlinear, multilevel and outlier-dependent
analysis — which is exactly what harm detection is.

**But the caveat is weaker here than for text**, and this is worth being precise about. That
finding was measured largely against natural language and tabular records. You cannot
convincingly fake a person's sentence. You *can* convincingly fake an interaction graph —
degree distributions, temporal clustering, co-presence patterns, a group closing around
someone — because those are structural, and structure is what these analyzers consume. So
synthetic data carries further here than it usually does, and the honest boundary is:
**synthetic gets you working code; only code-to-data gets you validated findings.**

## 6. Open questions — where help is most wanted

1. **Are the twenty-six event types the right ones?** They came from one game. What is
   missing for a forum, a classroom tool, a voice platform?
2. **`proximity.avoid` is hard to emit.** Deliberate avoidance versus coincidence is a
   platform-side judgement with no obvious general definition. Is it one field, or several?
3. **Windowing.** Signals take a window; nothing says how to choose it. A four-session
   isolation and a four-month drift are different questions.
4. **Base rates and false positives.** Every false positive is a real person flagged to
   another person for something they did not do. What is an acceptable rate, and who decides?
5. **Cross-platform refs.** The same person on two platforms has two refs, deliberately.
   Is there any safe way to correlate, or is that a line that should never be crossed?
6. **Scoring.** `tools/score.py` reports recall and unexplained signals against planted
   shapes. That is a starting point, not a metric anyone should defend.
7. **Adversarial behaviour.** Everything here assumes participants are not trying to defeat
   it. That assumption fails eventually.
8. **Signal fatigue.** A reporting layer that surfaces everything trains its readers to
   ignore it. Suppression and aggregation are unspecified.

## 7. Not in scope

Identity verification, age assurance, content classification, enforcement, and appeals.
Adjacent, all necessary, none of them this.

## 8. Versioning

`schema_version` is required on every record. Additive changes bump the minor version;
removing or re-typing a field bumps the major. Emitters and analyzers state which they speak.

Draft 0.1.0. Nothing here has been run against a live deployment yet.
