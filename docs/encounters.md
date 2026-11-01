# Encounters

An Encounter authors the Evil side of one fight. It is stored separately from Player decks and uses their free-flow editor foundation: shared local draft persistence and creation reconciliation, card rows and previews, Gallery presentation, markup editing, and TTS clipboard reporting. Campaigns, runs, and Playtester are outside this feature.

## Authoring and visibility

In the Evil workspace, **Encounters** and **Build Encounter** appear in the navigation. The Encounters page has a scope toggle in its filter bar: **Public** lists valid public records, **Mine** (`/my/encounters`) lists the signed-in user's records across every visibility and validity state, and staff get **All** (`/staff/encounters`) to inspect every saved record. Notifications link to these scopes. All lists mirror Decks: header search with the result count and filters, illustrated summary cards, URL-backed name/faction filters, and an **All / Official / Community** filter (default All). Cards show the boss, summary, factions, counts, and update date; personal and management lists also show visibility and unfinished status. Official records have an **Official** badge. Lists load summary records, fetching full contents only for detail, editing, and export.

`creator` is the immutable owner. Owners can inspect all their saved work and edit/delete community Encounters. Staff can inspect, edit, and delete every Encounter. Only staff can set or clear `is_official`, including on unfinished work. Official status does not change ownership or visibility: an endorsed owner's Encounter remains in their **Mine** scope, but ordinary owners can no longer change any field, board, or delete it. Removing Official restores owner editing. The Details checkbox explains this protection; action visibility uses server-provided `can_edit` and `can_delete`.

Visibility defaults to **Private** (owner and staff only). **Unlisted** allows direct-link access when valid, without public discovery. **Public** appears in the public library when valid. Owners and staff can inspect incomplete records regardless of visibility. Official status grants no additional viewing/export access and remains independent of canonical faction assignments.

Personal routes are `/my/encounters`, `/my/encounters/new`, and `/my/encounters/:id/edit`. Public detail is `/encounters/:id`; staff management remains `/staff/encounters`. Legacy staff editor URLs redirect to personal editor routes, which also support staff editing other owners' records. Every Encounter route selects the Evil workspace.

Encounter detail mirrors Player deck detail: a sticky left panel shows the boss, creator, summary, visibility, and validity issues, while the right panel shows quantity-badged cards. Longer descriptions open in an adjacent details panel. Mainboard, named sideboard, and Boss tabs separate saved card collections from the selected boss and linked cards. The Boss tab is a viewing choice rather than another stored board. Sorting, card size, hover previews, type grouping, the loading skeleton, and the expandable layout use shared Player components. Detail sort/hover preferences are shared with Player deck detail; Encounter type grouping has its own saved preference. Card inspection links return to the Encounter and its originating public, personal, or staff library and its filters. TTS exports the selected sideboard independently; Mainboard and Boss tabs export the boss selection followed by the mainboard.

The builder uses the same workbench as Player decks: the shared filter bar in the page header, the scrolling card pool, the Encounter panel on the right, and a bottom bar with save state, autosync, counts, and validity. On narrow screens, the collection panel and its view switch appear above the card pool. While Details is open, the covered pool is inert and focus moves into Details; the collection panel remains usable. The Encounter panel switch reads **Boss · Cards · Details**: it switches the pool between Boss and Cards and opens **Details** as an overlay above the current pool; choosing a boss returns the pool to Cards. Cards and descriptions can be added before a boss. The header holds the Create/Save action. Details reuse the Player name/markup fields and choice pills. New work is saved automatically to a browser-local, per-user Encounter draft until **Create** is selected, even if incomplete. Saved records support explicit Save and optional autosync, including details edits. Autosync preference survives refresh, and enabling it also saves already-pending edits. Saved records are immediately shared with staff.

An Encounter stores a UUID, creator, timestamps, name, optional summary and long-description markup, nullable boss Card and selected CardGroup, an ordered mainboard and named sideboards with positive card quantities, faction assignments, visibility, Official status, and a revision. The model defaults to private visibility and non-official status. Canonical faction assignments are explicitly chosen from Order, Blood, Dark, Metal, and Fire; they are independent of boss factions and search filters. Difficulty and free-form tags are not included.

All picker requests explicitly use Evil. Boss selection includes standalone Evil Boss cards and group primary Boss cards with Gallery previews. Selecting a group stores that particular group, even when its primary belongs to multiple groups. All linked cards must be active Evil cards, but do not need the Boss role. Changing or clearing the boss preserves all manually added entries. Selecting a boss presets all its factions with match-any semantics; clearing it restores all factions. Builders can freely change those filters, and search and sorting remain intact.

Sideboards use the same board state and controls as Player decks (`useCardCollectionBoards` and `CardBuilderBoards` in the cards domain). Editors can add, select, rename, and delete boards, reorder entries, adjust quantities, and move one copy at a time between boards. Gallery additions and quantities target the selected board. Boss changes preserve every board. Sideboards are saved atomically with the Encounter under its revision, participate in drafts and autosync, and remain independent of Player copy or sideboard-quantity rules.

## Validity and lifecycle

Incomplete records can always be saved. Public discovery requires public visibility. Shared public/unlisted detail requires all of:

- Public or unlisted visibility and a nonblank name.
- An active Evil Card with the Boss role, and a compatible selected group if present.
- At least 20 manually added deck cards, counting quantities. Automatically included boss cards and sideboard cards do not contribute.
- Every referenced card, including sideboard and linked boss cards, remaining active and Evil.

The API exposes the core minimum through `GET /encounters/rules`. Player copy limits, mana requirements, legendary restrictions, and card-specific Player rule overrides do not apply. Manually added Evil cards have no extra role restriction.

Deprecation, reclassification, and group edits do not silently remove contents. They make affected Encounters invalid and remove public discovery and shared detail access until repaired. Export validates only its selected board. Owners and staff retain inspection access and see validity issues. An unchanged or reduced reclassified entry may round-trip while editors repair it; adding or increasing a non-Evil reference is rejected. A group selected by an Encounter cannot be deleted until its selection is changed. Card merges retarget Encounter references, combine duplicate quantities in saved order, and advance the revision.

## Durable creation and edit conflicts

`frontend/src/shared/drafts/` owns the persistence and creation state machines used by both builders. Shared workspace, save status, and recovery/conflict dialogs live in `frontend/src/shared/components/builders/`; card builder filters, gallery, details fields, selection previews, summary headers, and rows live in `frontend/src/domain/cards/components/`. Player feature components adapt their existing controller to those shared components. Encounter codecs use `card-reader.encounter-editor.new-draft.<user>`; Player storage remains separate and compatible with existing drafts. Recovery retains details, named sideboards, ordering, quantities, boss/group selection, faction assignments, and card snapshots while refreshing current identities.

Create uses an immutable payload and creator-scoped UUID idempotency key. A committed database transaction containing the Encounter, mainboard entries, sideboards and their entries, and creation receipt is authoritative success. An uncertain response is reconciled by creation-key lookup; retries use the same key and payload. Used keys survive deletion and return a deleted outcome rather than recreating the record.

Browser storage, network delivery, and navigation fail independently. Local cleanup is best effort and never reverses a committed create or initiates another one. Cross-tab writes use conditional storage revisions and browser locks; conflicts require an explicit choice. Without usable storage/locks, work stays in memory with a leave warning. Existing server updates require the current revision; a conflict preserves local edits and pauses autosync until the editor reloads the saved version. The conditional write checks ownership, current Official status, and revision atomically; stale editor state cannot bypass endorsement. A permission rejection stops autosync, locks mutations, retains unsaved changes in the editor, and offers navigation to the read-only saved record. Legacy drafts without Official data recover normally; unresolved creation payloads and keys are never rewritten. Reconciliation of an endorsed creation opens its read-only detail without another create.

## API

| Endpoint | Behavior |
| --- | --- |
| `GET /encounters` | Valid public summaries; `q`, repeated `factions`, optional `is_official=true\|false`, `page`, and `page_size` |
| `GET /encounters/{id}` | Owner/staff inspection, or valid public/unlisted detail |
| `GET /encounters/rules` | Minimum count and Evil pool metadata |
| `GET /encounters/bosses` | Authenticated grouped Gallery picker, forced active Evil/Boss scope and Boss group primaries |
| `GET/POST /my/encounters` | Owner summaries / authenticated creation, including incomplete work; UUID `Idempotency-Key` required on create |
| `GET/PATCH/DELETE /my/encounters/{id}` | Owner access with staff override; Official protection applies to mutations |
| `GET /my/encounters/by-creation-key/{key}` | Creator-scoped reconciliation: 200 found (possibly read-only), 404 unused, 410 deleted |
| `GET/POST /staff/encounters` | Compatible staff-only all-record listing / creation |
| `GET/PATCH/DELETE /staff/encounters/{id}` | Compatible staff-only management using the same mutation policy |
| `GET /staff/encounters/by-creation-key/{key}` | Staff-only alias for creator-scoped reconciliation |
| `GET /staff/encounters/bosses` | Staff-only alias for the boss picker |
| `GET /encounters/{id}/exports/tts` | Owner/staff or public/unlisted visibility, then mainboard/boss validation |
| `GET /encounters/{id}/exports/tts?sideboard_id={boardId}` | Same authorization, then selected sideboard validation only; no boss required |

PATCH requires `revision`; DELETE requires `If-Match` revision. Stale permitted mutations return 409; Official protection returns 403 even when the revision is stale. Other owners' management records are unavailable (404). Fixed paths are registered before dynamic ID routes. All three libraries accept the same filters; omitted `is_official` means All. My Encounters always filters by creator, including for staff.

Write fields are `name`, `description_markup`, `long_description_markup`, `boss_card_id`, `boss_group_id`, `factions`, `visibility` (`private`, `unlisted`, or `public`), `entries` (`card_id`, `quantity` in saved array order), and `sideboards` (`id` for an existing board, `name`, and ordered `entries`). Omit `sideboards` on PATCH to preserve them; supply an empty array to remove them. Existing IDs must belong to this Encounter and must not repeat. Sideboard names must be nonblank, quantities positive, and cards distinct within each board. New boards receive server-owned IDs. Only staff may submit `is_official`; ordinary submissions are rejected even when false. Summaries include `is_official`, `can_edit`, `can_delete`, attribution, revision, boss preview, counts, and computed status; detail adds hydrated mainboard/sideboard entries, boss cards, and markup. Summaries expose `sideboard_count` without loading board contents. Pagination follows the existing `count`, `page`, `page_size`, `next_page`, `previous_page`, `results` envelope.

## TTS export

Export uses `card-reader.tts-cards.v3`, persistent Evil sheets, and the existing bulk card-back resolver. One pile contains the boss selection followed by saved entries. Group membership is resolved at export time: primary and linked cards appear once in group order, with `boss` roles. Manually added entries retain order and quantities with `mainboard` roles, including deliberate extra boss-card copies.

Boss/group incompatibility and missing required artwork or backs fail explicitly. Ordinary unavailable artwork uses existing skipped-card reporting. Authorize exports by owner, staff, or public/unlisted visibility before validating the requested board. Full Encounter validity, name, and the 20-card minimum are not prerequisites. Main exports require a usable active Evil boss/group and compatible mainboard; unrelated invalid sideboards do not block them. Collection metadata includes Encounter identity, selected boss/group, and assigned factions. Targeted sideboard exports add `sideboard_id` and `sideboard_name`, use `sideboard` roles, and create one separate pile in saved order with no boss cards. A usable sideboard may be exported without a boss or usable mainboard; other sideboards are irrelevant. Private exports remain restricted to owner/staff, and Official status grants no extra access. See the [TTS guide](../tts/README.md).
