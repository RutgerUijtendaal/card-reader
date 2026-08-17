# Campaign Building Plan

Status: proposed direction, retained for future design and implementation work.

This document preserves the initial campaign-building product idea and the architectural conclusions reached after reviewing the card-classification branch against `master`. It is not a final schema or implementation specification. Decisions marked as open must be resolved before migrations or public API contracts are created.

## Product goal

The primary game-start flow should let a GM select the material needed to bootstrap a complete game rather than exporting and assembling every pile independently.

The intended flow is:

1. The GM selects a Faction.
2. The GM selects a published Campaign.
3. The GM selects the Player Decks participating in the game.
4. Card Reader validates and resolves the selections into the exact piles required by the Campaign.
5. The GM exports the complete setup to Tabletop Simulator.
6. The TTS importer creates the separate decks, piles, or containers needed to start playing.

A Campaign is expected to contain an ordered set of boss fights, reusable or campaign-specific Boons, Events, Shop Items, shared setup material such as Mana, and any additional pile types introduced later.

## Architectural conclusion

The card-classification work provides the correct foundation for selecting and validating Cards, but Campaign composition belongs in a new domain layer above Card classification and Player Decks.

The four stable Card dimensions have the right responsibilities:

- `card_pool` identifies Player, Evil, or Neutral content.
- `card_roles` identifies intrinsic Card roles such as Hero, Boss, Location, Boon, Event, Shop Item, Directive, Reminder, and Mana.
- `card_factions` identifies one or more intrinsic Factions.
- `card_mana_families` identifies one or more intrinsic Mana families.

These dimensions should be usable as predicates in Campaign and pile rules. They should not store Campaign placement or progression state.

Examples of the boundary:

- "This Card is a Boss" is intrinsic Card classification.
- "This Card is the boss of the third Encounter" is Encounter membership.
- "This Mana pile is loaded once for the Campaign" is Campaign pile scope.
- "This Boon is awarded after the second Encounter" is Campaign progression or reward placement.

Do not add Card roles to represent contextual placement when the fact belongs to a Campaign, Encounter, pile, or resolved game setup.

## Preserve existing domain meanings

### Player Deck

Keep the existing `Deck` aggregate as a Player Deck. It has coherent, deliberately Player-specific semantics: an owner, a Hero, a mainboard, sideboards, Player-only validation, visibility, Playtester behavior, and deck-specific TTS export.

Do not rename the current model to `Collection` or turn it into a mixed-pool container. Reusable implementation details such as ordered entries, quantities, selection controls, and validation presentation may be shared without collapsing the domain models.

Player Decks should normally be inputs selected by the GM when creating a game setup. A staff-authored Campaign should declare its Player Deck requirements rather than embedding arbitrary user-owned Deck rows. Curated preconstructed Player Decks can be supported later as an explicit case.

### Card Group

Keep Card Groups for related Card identities such as variants or alternate printings. They have an anchor and ordered members but no quantity, pile, ownership, publication, or gameplay-rule semantics. They are not Campaign collections.

### Import classification rules

`CardClassificationRule` is an import-time inference mechanism. It maps detected Tags, Types, or Symbols to intrinsic Card Roles, Factions, or Mana Families. It is not a general game-rule engine.

Campaign work must not extend import inference rules with quantities, collection scopes, encounter ordering, or progression. To keep the distinction clear when the second rule system is introduced, consider renaming the import concept to `CardClassificationInferenceRule`.

### Player Deck constraints

The existing deck constraint evaluator is intentionally closed around Player Deck rules and the `mainboard` and `whole_deck` scopes. It should not be generalized into the Campaign rule engine.

The current evaluator also applies conflicting Card-provided deck-level overrides sequentially in Card-id order. That behavior is deterministic but is not a meaningful composition rule. A future pile or Campaign evaluator must define how every rule kind combines or reject incompatible rules explicitly.

## Proposed terminology and aggregates

Use specific product nouns rather than the broad backend name `Collection` unless later design work finds a meaning that is both precise and stable.

### Pile Definition and Pile Revision

A reusable, staff-authored description of one logical pile or container.

A published Pile Revision should define:

- a stable pile key and display name;
- a pile kind, such as Event, Boon, Shop, setup, boss deck, or another code-owned kind;
- fixed Card entries and quantities where the content is curated exactly;
- typed selector rules where content is resolved from Card classifications;
- ordering and shuffle behavior;
- minimums, maximums, and other validation rules;
- whether unavailable or deprecated Cards invalidate resolution;
- optional TTS container and placement hints.

Fixed entries should be relational records. Selector and constraint payloads may use a versioned, typed representation, but should not become an unvalidated arbitrary JSON rule language.

### Encounter Revision

An immutable, published boss-fight definition. An Encounter may reference or own typed slots for:

- one or more Boss Cards;
- the fight deck or fight-specific Evil piles;
- Locations, Directives, Reminders, and setup material;
- rewards or Boons unlocked by the fight;
- additional encounter-specific piles;
- ordering and presentation instructions.

Boss Cards and fight placement should be explicit Encounter membership. A Card having the Boss role is an eligibility predicate, not enough by itself to define a fight.

### Campaign Revision

An immutable, published Campaign definition containing:

- an ordered sequence of Encounter Revisions;
- shared piles loaded once for the whole Campaign;
- campaign-specific Event, Boon, and Shop piles;
- Faction requirements or parameterized selectors;
- Player Deck slot requirements;
- Campaign metadata and instructions;
- a versioned rules/schema contract.

The existing documentation uses `Scenario` as a placeholder for a future mixed-content aggregate. Before implementation, standardize the vocabulary. The proposed distinction is that a Campaign is the complete sequence while an Encounter is one boss fight. Retain `Scenario` only if it receives a separate, precise product meaning.

### Game Setup

A GM-owned request to start or prepare a game. It records the chosen:

- Campaign Revision;
- Faction;
- Player Decks;
- any other Campaign parameters.

Creating a Game Setup should resolve its inputs through the authoritative core service rather than letting the frontend independently construct the final piles.

### Resolved Campaign Manifest

An immutable result containing the exact material selected for one game setup:

- Campaign and revision identity;
- selected Faction and Player Deck identities;
- ordered Encounters;
- logical pile identities and kinds;
- exact Card IDs, quantities, and positions per pile;
- the rules/schema version used to resolve the setup;
- validation warnings and blocking failures;
- export-time CardVersion IDs, image checksums, or another explicit artwork policy.

The resolved manifest is the boundary between Campaign rules and downstream consumers such as TTS export. Exports should consume the manifest rather than rerunning mutable authoring rules independently.

## Rule and selector requirements

The first rule vocabulary should remain small and typed. Likely Card predicates include:

- exact `card_pool`;
- explicit Card IDs;
- Role inclusion, exclusion, and `any` or `all` matching;
- Faction inclusion, exclusion, and `any` or `all` matching;
- Mana Family inclusion, exclusion, and Colorless matching;
- active/deprecated lifecycle behavior;
- bounded quantities and unique-Card counts.

Tags, Types, Symbols, and parsed numeric fields belong to `CardVersion`. They may be useful selectors, but using them makes resolution depend on mutable version metadata. Each such selector must therefore define whether it resolves against the current latest version, a published Campaign snapshot, or pinned CardVersion records.

Rule composition must be defined per rule kind. Examples include:

- minimum constraints combine by taking the strongest minimum;
- maximum constraints combine by taking the strongest maximum;
- exclusions accumulate;
- mutually incompatible requirements produce a blocking conflict;
- no rule should win merely because its database identifier sorts later.

The evaluator should return structured violations with stable codes, scopes, severity, affected pile or Card identities, and human-readable messages. The frontend should render these results rather than reimplement rule semantics.

## Publication and versioning

Staff authoring and GM consumption need a publication boundary.

- Draft definitions remain editable.
- Published revisions are immutable.
- Editing published content creates a new revision.
- Campaign Revisions reference explicit Pile and Encounter revisions rather than mutable latest definitions.
- Existing Game Setups and manifests retain the revisions against which they were resolved.

Before implementation, decide when selector-based content is frozen:

- at Pile or Campaign publication;
- when the GM creates a Game Setup;
- when the GM exports to TTS.

Resolving at Game Setup creation offers fresh Card classifications while preserving one prepared game's exact contents. Publication-time resolution offers stronger curation and review. A hybrid may allow explicitly fixed piles alongside parameterized piles resolved from the selected Faction.

## Stateful workflow boundary

The Game Setup workflow must define the following before browser and server mutations are implemented:

- **Authoritative success:** a durable Resolved Campaign Manifest has been committed for the requested setup.
- **Idempotency boundary:** retries of the same immutable setup request return the same setup and manifest rather than creating duplicates or resolving against newer data.
- **Independent failure domains:** manifest creation, TTS encoding, clipboard handling, navigation, and local browser cleanup are separate outcomes.
- **Cleanup semantics:** failure to clear a local draft or navigate must not reverse or repeat an already confirmed server-side setup.

The immutable attempt must include the selected Campaign revision, Faction, Player Deck IDs, and all other resolution parameters.

## Tabletop Simulator direction

The current persistent TTS sheet system already provides useful groundwork:

- Card sheet slots use stable Card identities;
- sheets are partitioned by Player, Evil, and Neutral pools;
- one export may reference sheets from multiple pools;
- CardVersion IDs and image checksums are included at export time.

The current payload still describes one flat collection and the importer creates one native deck. Its optional `cards[].role` field represents export placement such as Hero, mainboard, or sideboard; it must not be overloaded with intrinsic Card Roles or Campaign pile identity.

A Campaign-capable payload will likely need a new schema version with:

- multiple logical piles;
- stable `pile_id` or slot keys on entries;
- pile names, kinds, order, and shuffle behavior;
- container or spawn instructions;
- Campaign and Encounter metadata;
- exact relationships between Cards and piles;
- support for spawning several decks, piles, bags, or standalone Cards from one manifest.

Sheet allocation can remain pool-partitioned underneath the export. Campaign pile boundaries and sheet boundaries are independent concerns.

## Staff authoring direction

Staff should be able to build and publish reusable piles, Encounters, and Campaigns. Frontend builders may share a common card-selection and ordered-entry surface, but each feature should retain its domain-specific workflow and validation.

A likely authoring sequence is:

1. Create reusable or Campaign-local Pile Definitions.
2. Build and validate Encounter drafts from Boss Cards and fight-related piles.
3. Compose ordered Encounters and shared piles into a Campaign draft.
4. Preview resolution for each supported Faction and representative Player Deck inputs.
5. Publish immutable revisions only after all hard validation passes.

Previewing must show exactly why Cards qualify for selector-based slots and should surface deprecated, missing-artwork, ambiguous, or underfilled results before publication.

## Open product and schema decisions

Resolve these before creating migrations:

- Are Piles always reusable definitions, or may a Campaign own private inline piles?
- Can Piles contain only Cards, or can they reference other Piles? If nesting is allowed, how are cycles prevented and expansion bounded?
- Are selector results frozen at publication, setup creation, or export?
- Does a Campaign support one Faction, a set of Factions, or a required runtime Faction parameter?
- May multi-Faction Cards satisfy one selected Faction through containment, or are some slots exact-Faction only?
- How many Player Deck slots exist, and can their validation vary per Campaign?
- Are Player Decks merely setup inputs, or can Campaigns provide curated preconstructed decks?
- What makes a Boss Fight structurally different from another Card pile?
- Which piles are global to a Campaign, Encounter-local, rewards, or progression-dependent?
- Must one Game Setup persist beyond export, or is the durable manifest primarily an export/reproducibility record?
- How are Campaign ownership, visibility, publication permissions, and archival handled?
- What happens when referenced Cards become deprecated, are merged, or receive new latest artwork?
- Should `CardClassificationRule` be renamed before the Campaign rule vocabulary is introduced?

## Suggested delivery checkpoints

1. **Terminology and invariant specification**
   - Finalize Campaign, Encounter, Pile, Game Setup, and manifest meanings.
   - Decide publication and selector-freezing semantics.
   - Define ownership, visibility, lifecycle, and idempotency.

2. **Core resolution prototype**
   - Implement typed in-memory inputs, selector predicates, rule composition, structured violations, and deterministic manifest output without adding the full UI.
   - Test resolution against multi-role, multi-Faction, multi-Mana-family, Neutral, deprecated, and merged Cards.

3. **Persistence and publication**
   - Add Django-owned models and migrations for drafts and immutable revisions.
   - Add repositories and core services with strict API/core layering.
   - Update the database diagram and developer-data policy if published Campaign content belongs in development bundles.

4. **Staff builders**
   - Build shared entry-selection components where the abstraction fits.
   - Add domain-specific Pile, Encounter, and Campaign authoring workflows.
   - Support previews across light and dark themes.

5. **GM game setup flow**
   - Select Faction, Campaign revision, and Player Decks.
   - Resolve idempotently into one immutable manifest.
   - Present blocking errors, warnings, and exact pile previews.

6. **Campaign TTS export**
   - Add a multi-pile payload version and importer behavior.
   - Preserve existing deck, sideboard, gallery, and content-version exports.
   - Verify mixed-pool sheets and separate logical pile spawning.

## Initial acceptance criteria

The first usable Campaign slice should demonstrate that:

- staff can publish one Campaign with shared piles and at least two ordered boss Encounters;
- a GM can select a Faction, that Campaign revision, and Player Decks;
- all Card selection uses the stable classification layer and explicit lifecycle rules;
- the backend produces one deterministic, immutable manifest with distinct piles;
- retrying the same setup request cannot create or resolve a different setup;
- TTS export spawns the required Player, Evil, Neutral, setup, and reward piles separately;
- later Card or Campaign edits cannot silently alter the stored manifest;
- existing Player Deck, Playtester, Card Group, import inference, and TTS deck behavior remains intact.
