# Implementation — the reference emitter, and the tables you can create today

`SPEC.md` describes a contract any platform could satisfy. This file is the concrete half:
the physical tables, what each one is for, and how a platform fills them. If you want to
adopt this, **you do not have to design a database. It is in
[`reference/watcher-schema.sql`](reference/watcher-schema.sql), and you can run it now.**

The reference emitter is **CocoonMinis**, the server plugin behind
[The Cocoon Collective](https://github.com/The-Cocoon-Collective) — a Minecraft world for
six- and seven-year-olds. Nothing below is Minecraft-shaped in a way that matters. A forum, a
classroom tool or a voice platform fills the same nine tables with different verbs.

---

## 1. The whole idea in one table row

Every row in this schema, in every table, answers the same five questions:

```
   event_type        who           where                    who else     when
   ─────────────     ──────────    ─────────────────────    ─────────    ────
   family.type       participant   server / world / x,y,z   others       at
```

Four of those five are standard. **The fifth is the one almost nobody writes down, and it is
the difference between a one-dimensional record and a three-dimensional one.**

`others` is who else was in range **at the moment the event was written**. It cannot be
reconstructed afterwards by joining two streams on timestamps — presence has duration, events
have instants, and "in range" is a judgement only the platform can make, and only at the time.

This is what makes the record correlatable. Chat alone is searchable and thin. Position alone
is a heat map. **The signal is in the join:** what was said, by whom, while standing where,
with whom else present, doing what. That join is only possible because every row carries its
own spatial and social context.

If you take one thing from this repository, take that column.

---

## 2. Nine tables, twenty-eight observation types

| table | types it carries | what it is for |
|---|---|---|
| `session_events` | `session.begin` `session.end` | when someone was present at all, and for how long |
| `sightings` | `presence.enter` `presence.leave` `presence.dwell` | where they went, and whether they stayed |
| `proximity_events` | `proximity.copresence` `proximity.follow` `proximity.avoid` | who they were near, who they tracked, who they steered clear of |
| `interaction_events` | `interaction.direct` `assist` `obstruct` `exchange` | what they did to or with each other |
| `affiliation_events` | `affiliation.form` `join` `leave` `remove` `invite` `decline` | groups forming, and people being put out of them |
| `artifact_events` | `artifact.create` `modify` `destroy` | what they made, and what got broken |
| `transfer_events` | `transfer.value` | economy, gifts, and sustained one-way giving |
| `chat_events` | `communication.utterance` `communication.direct` `communication.voice` | that something was said, or that a voice channel was shared — never what was said in it |
| `moderation_events` | `moderation.action` `moderation.report` `moderation.repair` | the platform's own interventions, including the ones that put something right |

Plus `watcher_meta`, a two-column key/value table holding the schema version, so an operator
can ask the database what it thinks it is without reading any code.

**Twenty-five of the twenty-eight types carry no communication at all, and the three that
do carry no content.** That ratio is the design claim. Keyword moderation can read exactly
one of the twenty-eight — `communication.utterance`, the typed one. This schema is built for
the other twenty-seven.

`communication.voice` and `moderation.repair` were added in 0.2.0 and need no new table:
`event_type` is a `VARCHAR` in both, and the additive migrations at the foot of
`reference/watcher-schema.sql` add the three columns voice needs. **No emitter writes either
type yet** — they are defined ahead of the features they describe, on purpose.

### The four rows that matter most, and why

- **`affiliation.remove`** — somebody being put out of a group by somebody else. The actor
  and the subject are separate columns for exactly this reason: the participant an event is
  *about* is usually not the participant who caused it.
- **`proximity.avoid`** — somebody steering clear. Absence is a signal, and absence is only
  visible if you record it. Record the *measurement* — repeatedly in the same scope,
  repeatedly did not close — never the conclusion.
- **`transfer.value` with nothing pointing back** — `reciprocal_of` links a transfer to the
  one it repays. A chain with nothing reciprocating it is a measurable imbalance, and nobody
  has to form an opinion for it to be visible.
- **`moderation.action`** — this is not bookkeeping. An analyzer that cannot see somebody was
  muted on Tuesday will read the silence that followed as withdrawal.

### The distinction that turns a door counter into an encounter detector

`presence.enter` and `presence.dwell` are **different observations and must not come from the
same threshold.** Somebody crossing a room is not interesting. Somebody who stops for thirty
seconds in a room where another participant already is, is. `sightings.duration_ms` is what
separates them, and one configuration value decides which one you are collecting.

---

## 3. Three layers, and the middle one is the design

```
  the platform's own store          the emitter              this repo
  ───────────────────────          ───────────               ─────────
  identified, complete,      →     projects, strips,   →     observations
  private forever                  pseudonymises             (public format)
```

**The tables in `reference/watcher-schema.sql` are the first layer.** They hold real account
ids and real message text on purpose. They have to: a platform that cannot answer "what
exactly happened to this child" cannot be run responsibly, and a guardian asking that question
deserves an answer.

**An observation is a projection of that store, not a copy of it.** The emitter is where an
account id becomes a `ref` and an utterance becomes a `content_ref` plus a length. That is why
`chat_events` has both `message` and `content_ref` — the first never leaves, the second is
what travels.

The naive reading of the README — "the schema has no field for a name, therefore the platform
holds no names" — is wrong, and would be a bad thing to be true. **The platform holds names.
The schema is what stops them travelling.**

### Where a `ref` comes from

Keep a registry mapping a real account id to a stable, opaque participant id, and let that id
be the only thing a family, a report or an observation ever sees. It is a cipher layer, not a
hash of anything guessable, and the mapping is never published. Build it **before** the
emitter — retrofitting it means rewriting every row you have already emitted.

`cohort` comes from your own age or segment banding, kept deliberately coarse.
`tenure_days` comes from first-seen.

---

## 4. Adopting this

1. **Run `reference/watcher-schema.sql`** against an empty database of its own. Not your game
   database, not your accounts database — its own credentials, its own retention, its own
   backup. A deletion request should touch one database.
2. **Fill the boring families first** — `session_events` and `sightings`. They are cheap,
   they are most of the volume, and they are enough to test an analyzer end to end.
3. **Write `others` from the first row.** Everything else can be added later; that column
   cannot be backfilled.
4. **Build the ref layer before the emitter.**
5. **Leave content out of anything that travels.** A `content_ref` you never resolve costs
   nothing. A message body in a published stream cannot be recalled.
6. **Validate in CI** — `tools/validate.py` exits non-zero on failure, so an emitter that
   breaks the contract fails its own build rather than someone's dashboard at 2am.

### Your verbs are not our verbs, and that is fine

`interaction_events.verb`, `artifact_events.artifact_kind` and `affiliation_events.group_kind`
are deliberately open strings — a closed vocabulary in *your* emitter, not in this schema. A
Minecraft platform writes `block_place`; a forum writes `thread_reply`; a classroom tool
writes `worksheet_shared`. The **shape** is what the analyzers consume, and the shape is the
same.

⚠ One rule about them: they must never carry free text authored by a person. That is what
`content_ref` is for.

---

## 5. Many producers, one stream

`source.platform` and `source.emitter` exist so one store can hold several producers. Any
plugin — an economy system, a minigame, a moderation tool, someone else's mod entirely — can
write into the same tables without knowing anything about the others, and an analyzer can
weight them differently or ignore one.

**A published contract gets many producers for free. A shared library gets one**, in one
language, on one release schedule. That is the argument for this being a schema rather than
an SDK, and it is why a platform running an entirely different game can contribute to the same
stream.

---

## 6. Where the reference emitter is

The tables are created on every boot by `WatcherDatabase` in CocoonMinis, and the SQL in this
repository is generated from that same code, so the two cannot drift.

**Populated today:** `session_events`, `sightings`, `chat_events` — the plugin's collection
layer is live and writing.

**Created and waiting:** `proximity_events`, `interaction_events`, `affiliation_events`,
`artifact_events`, `transfer_events`, `moderation_events`. These are the data points the main
game will emit as each subsystem is wired to them. They exist first on purpose — a platform
adopting this sees the whole surface it is expected to fill on day one, rather than
discovering it a family at a time and migrating six times.

Two things are honestly still ahead of us and are the most interesting work in the repository:
the projection from these tables into the published observation format, and an analyzer good
enough to beat the deliberately weak one in `tools/`.

Both are open, and both are more fun than they sound. See [SPEC.md](SPEC.md) §6 and
[CONTRIBUTING.md](CONTRIBUTING.md).
