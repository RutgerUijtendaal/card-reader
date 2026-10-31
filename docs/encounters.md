# Encounters

An Encounter authors the Evil side of one fight. It is stored separately from Player decks and uses their free-flow editor foundation: shared local draft persistence and creation reconciliation, card rows and previews, Gallery presentation, markup editing, and TTS clipboard reporting. Campaigns, runs, and Playtester are outside this feature.

## Authoring and visibility

In the Evil workspace, **Encounters** lists valid public records. **Staff Encounters** lists all saved records for staff, with name search and match-any filtering by assigned faction tags. Both lists mirror Decks: a left search/faction sidebar with Public/Staff library tabs and a single column of illustrated summary cards. Cards show boss artwork, summary, assigned factions, card count, and update date. Staff cards also expose creator, visibility, unfinished status, and editing, regardless of who created the Encounter. Search and faction selections are URL-backed and retained between library tabs; more summaries load as the list scrolls. The illustrated card and loading skeleton are shared with Player deck lists. All staff can create, edit, delete, and inspect any saved Encounter. Direct Encounter routes select the Evil workspace.

Encounter detail mirrors Player deck detail: a sticky left panel shows the boss, creator, summary, visibility, and validity issues, while the right panel shows quantity-badged cards. Longer descriptions open in an adjacent details panel. Mainboard, named sideboard, and Boss tabs separate saved card collections from the selected boss and linked cards. The Boss tab is a viewing choice rather than another stored board. Sorting, card size, hover previews, type grouping, the loading skeleton, and the expandable layout use shared Player components. Detail sort/hover preferences are shared with Player deck detail; Encounter type grouping has its own saved preference. Card inspection links return to the Encounter and its originating public/staff library. TTS exports the selected sideboard independently; Mainboard and Boss tabs export the boss selection followed by the mainboard.

The builder has peer **Boss**, **Details**, and **Cards** sections. Cards and descriptions can be added before a boss. Boss and Cards use the same three-column workspace as Player decks: shared filters on the left, the shared scrolling gallery in the center, and the selected boss or ordered deck on the right. The header has section tabs and Create/Save actions; the status bar shows save state, autosync, counts, and validity. Details reuse the Player name/markup fields and choice pills. New work is saved automatically to a browser-local, per-user Encounter draft until **Create** is selected, even if incomplete. Saved records support explicit Save and optional autosync, including details edits. Autosync preference survives refresh, and enabling it also saves already-pending edits. Saved records are immediately shared with staff.

An Encounter stores a UUID, creator, timestamps, name, optional summary and long-description markup, nullable boss Card and selected CardGroup, an ordered mainboard and named sideboards with positive card quantities, faction assignments, visibility, and a revision. The model defaults to staff-only visibility. Canonical faction assignments are explicitly chosen from Order, Blood, Dark, Metal, and Fire; they are independent of boss factions and search filters. Difficulty and free-form tags are not included.

All picker requests explicitly use Evil. Boss selection includes standalone Evil Boss cards and group primary Boss cards with Gallery previews. Selecting a group stores that particular group, even when its primary belongs to multiple groups. All linked cards must be active Evil cards, but do not need the Boss role. Changing or clearing the boss preserves all manually added entries. Selecting a boss presets all its factions with match-any semantics; clearing it restores all factions. Staff can freely change those filters, and search and sorting remain intact.

Sideboards use the same board state and controls as Player decks (`useCardCollectionBoards` and `CardBuilderBoards` in the cards domain). Staff can add, select, rename, and delete boards, reorder entries, adjust quantities, and move one copy at a time between boards. Gallery additions and quantities target the selected board. Boss changes preserve every board. Sideboards are saved atomically with the Encounter under its revision, participate in drafts and autosync, and remain independent of Player copy or sideboard-quantity rules.

## Validity and lifecycle

Incomplete records can always be saved. Public availability requires all of:

- Public visibility and a nonblank name.
- An active Evil Card with the Boss role, and a compatible selected group if present.
- At least 20 manually added deck cards, counting quantities. Automatically included boss cards and sideboard cards do not contribute.
- Every referenced card, including sideboard and linked boss cards, remaining active and Evil.

The API exposes the core minimum through `GET /encounters/rules`. Player copy limits, mana requirements, legendary restrictions, and card-specific Player rule overrides do not apply. Manually added Evil cards have no extra role restriction.

Deprecation, reclassification, and group edits do not silently remove contents. They make affected Encounters invalid and remove public list, detail, and export access until repaired. Staff retain access and see validity issues. An unchanged or reduced reclassified entry may round-trip while staff repair it; adding or increasing a non-Evil reference is rejected. A group selected by an Encounter cannot be deleted until its selection is changed. Card merges retarget Encounter references, combine duplicate quantities in saved order, and advance the revision.

## Durable creation and staff conflicts

`frontend/src/shared/drafts/` owns the persistence and creation state machines used by both builders. Shared workspace, save status, and recovery/conflict dialogs live in `frontend/src/shared/components/builders/`; card builder filters, gallery, details fields, selection previews, summary headers, and rows live in `frontend/src/domain/cards/components/`. Player feature components adapt their existing controller to those shared components. Encounter codecs use `card-reader.encounter-editor.new-draft.<user>`; Player storage remains separate and compatible with existing drafts. Recovery retains details, named sideboards, ordering, quantities, boss/group selection, faction assignments, and card snapshots while refreshing current identities.

Create uses an immutable payload and creator-scoped UUID idempotency key. A committed database transaction containing the Encounter, mainboard entries, sideboards and their entries, and creation receipt is authoritative success. An uncertain response is reconciled by creation-key lookup; retries use the same key and payload. Used keys survive deletion and return a deleted outcome rather than recreating the record.

Browser storage, network delivery, and navigation fail independently. Local cleanup is best effort and never reverses a committed create or initiates another one. Cross-tab writes use conditional storage revisions and browser locks; conflicts require an explicit choice. Without usable storage/locks, work stays in memory with a leave warning. Existing server updates require the current revision; a conflict preserves local edits and pauses autosync until staff reload the saved version.

## API

| Endpoint | Behavior |
| --- | --- |
| `GET /encounters` | Valid public summaries; `q`, repeated `factions`, `page`, and `page_size` |
| `GET /encounters/{id}` | Valid public detail |
| `GET /encounters/rules` | Minimum count and Evil pool metadata |
| `GET /staff/encounters` | All saved summaries with the same filters |
| `POST /staff/encounters` | Create, including incomplete drafts; UUID `Idempotency-Key` required |
| `GET /staff/encounters/bosses` | Staff boss picker using grouped Gallery filters, forced active Evil/Boss scope and Boss group primaries |
| `GET /staff/encounters/{id}` | Full shared staff record |
| `PATCH /staff/encounters/{id}` | Partial update with required `revision`; stale writes return 409 |
| `DELETE /staff/encounters/{id}` | Delete with required `If-Match` revision; stale deletes return 409 |
| `GET /staff/encounters/by-creation-key/{key}` | Creator-only reconciliation: 200 found, 404 unused, 410 deleted |
| `GET /encounters/{id}/exports/tts?sideboard_id={boardId}` | Selected sideboard only; same visibility gate, staff can export without a boss |
| `GET /encounters/{id}/exports/tts` | Public valid records, or structurally usable unfinished records for staff |

Write fields are `name`, `description_markup`, `long_description_markup`, `boss_card_id`, `boss_group_id`, `factions`, `visibility` (`private` or `public`), `entries` (`card_id`, `quantity` in saved array order), and `sideboards` (`id` for an existing board, `name`, and ordered `entries`). Omit `sideboards` on PATCH to preserve them; supply an empty array to remove them. Existing IDs must belong to this Encounter and must not repeat. Sideboard names must be nonblank, quantities positive, and cards distinct within each board. New boards receive server-owned IDs. Summaries include attribution, revision, boss preview, counts, and computed status; detail adds hydrated mainboard/sideboard entries, boss cards, and markup. Summaries expose `sideboard_count` without loading board contents. Pagination follows the existing `count`, `page`, `page_size`, `next_page`, `previous_page`, `results` envelope.

## TTS export

Export uses `card-reader.tts-cards.v3`, persistent Evil sheets, and the existing bulk card-back resolver. One pile contains the boss selection followed by saved entries. Group membership is resolved at export time: primary and linked cards appear once in group order, with `boss` roles. Manually added entries retain order and quantities with `mainboard` roles, including deliberate extra boss-card copies.

Boss/group incompatibility and missing required artwork or backs fail explicitly. Ordinary unavailable artwork uses existing skipped-card reporting. Staff may export without a name or 20 cards, but the boss and every referenced identity must remain structurally compatible. Public export also requires current public validity. Collection metadata includes Encounter identity, selected boss/group, and assigned factions. Targeted sideboard exports add `sideboard_id` and `sideboard_name`, use `sideboard` roles, and create one separate pile in saved order with no boss cards. Staff may export a usable sideboard before selecting a boss; public access still requires validity of the entire Encounter. See the [TTS guide](../tts/README.md).
