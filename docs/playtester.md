# Playtester

Playtester is a frontend-only manual sandbox for trying a saved deck. It models physical card copies, zones, piles, and opening-hand setup, but deliberately does not implement a rules engine or persist game state to the backend.

## Entry points and deck loading

The deck selector lives at `/playtester`; an active session lives at `/playtester/:deckId`. Selection uses deck summaries for browsing and loads full deck detail only when it needs card entries for previewing or play.

Starting a playtest expands mainboard quantities into distinct `PlaytestCardInstance` copies. Sideboards remain reference-only, and the hero begins in its dedicated stack outside the library.

Playtester consumes Player-pool decks only. Until decks persist their own classification, every deck supported by the current builder is treated as a Player deck. Once explicit deck pools exist, the selector and direct play route must omit or reject Evil and Neutral decks rather than inferring eligibility from their current card contents.

The pool workspace does not show Playtester in Evil or Neutral navigation. A direct Playtester route switches the global workspace to Player, while deck and card eligibility independently reject non-Player references. A future non-Player testing workflow would be a separate design; the current hero, opening-hand, and mainboard assumptions must not be generalized into one automatically.

Hero-zone behavior follows the card's Hero role through the shared deck contract; Playtester does not maintain a separate Hero boolean or infer classification from card text.

## Opening setup

New sessions begin in an opening phase. The player can reserve exact physical mana or setup cards across mulligans, inspect an opening-hand preview, and keep a hand when ready. Keeping the hand establishes the starting draft and transitions the table into normal play.

This setup is intentionally manual. It supports testing real deck behavior without pretending to enforce all game-specific mulligan or play rules.

## Table interactions

The play surface supports the physical operations needed for manual testing:

- moving cards between the library, hand, board, discard, exile, and relevant stacks;
- pointer dragging and drag-box group selection;
- stacks and visual piles, including card-level inspection;
- right-click context actions;
- keyboard shortcuts for common actions;
- hold-only middle-click card zoom;
- a local card-scale preference shared by the selector and active table.

Reusable table, lower-bar, stack, and popover components keep preview and active-play behavior consistent.

## Local persistence

Draft state is stored locally per deck and tied to the deck's `updated_at` value. If the underlying deck changes, stale play state can be recognized instead of being applied blindly to a different deck composition.

No play state is uploaded to the server. Clearing browser storage or choosing to restart a playtest removes the local draft without changing the saved deck.

## State ownership

Playtester keeps its responsibilities separated:

- initialization and normalization live in `playtestStateCore.ts`;
- board mutations live in `playtestBoardState.ts`;
- opening setup lives in `playtestOpeningState.ts`;
- storage migration and serialization live in `playtestDraftPersistence.ts`.

This boundary matters when extending the feature: deck and card business logic belongs in the shared domain layers, while manual table interactions and local play state remain Playtester-owned.
