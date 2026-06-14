---
name: card-reader-playtester
description: Work on Card Reader's Playtester feature: deck selection, opening setup, manual board sandbox interactions, stacks, piles, drag selection, card zoom, and local playtest drafts.
---

# Card Reader Playtester

Follow `AGENTS.md` and `card-reader-frontend` first. Use this skill when changing `frontend/src/modules/playtester` or deck-list actions that route into playtesting.

## Feature Shape

- Keep Playtester frontend-only unless the user explicitly asks for backend persistence or server-side deck search.
- `/playtester` is a deck selector that should reuse existing deck list UI patterns and keep owned suggestions before public suggestions.
- `/playtester/:deckId` is a full-screen manual sandbox, not a data page. Preserve the board-like surface and avoid table/card-gallery layouts inside the active play area.
- Authenticated active playtests should try owned deck detail first, then public deck detail. Anonymous playtests should use public deck detail only.
- Sideboards are reference-only and must not enter the shuffled library.
- Drafts are local-storage only, keyed per deck plus `deck.updated_at`. Since V1 has not shipped broadly, do not add branch-era migration code unless explicitly requested.

## State Rules

- Treat each physical card copy as a `PlaytestCardInstance`; never model interactions only by card id.
- The hero starts in the `hero` stack and stays outside the shuffled library.
- Mainboard copies expand into the shuffled `library`.
- Valid zones are `library`, `hand`, `play`, `discard`, `banish`, `other`, and `hero`.
- Opening setup starts in phase `opening`; the main board is inaccessible until the user keeps an opening hand.
- Opening setup selections reserve exact physical mana/setup instances across mulligans.
- Mana cards are detected by a card type whose key normalizes to `mana`.
- Setup cards are detected by a keyword that normalizes to `setup`.
- Keeping the opening setup moves selected mana/setup instances onto the board, saves a setup snapshot, clears opening selections, and enters phase `play`.
- Reset to setup must restore the accepted setup snapshot exactly.

## Interaction Rules

- Use the custom pointer drag system, not native HTML drag/drop.
- `PlaytestDraggedCard` is first-class transient state and should render an actual fixed overlay card.
- Preserve pointer grab offset when dropping cards; dropping should not recenter cards under the pointer.
- Dragging selected board cards as a group should move all selected cards together and allow dropping the group into hand or stacks.
- Ctrl-dropping onto a board card creates or joins a visual pile at the target card's anchor. Pulling a card out removes only that card.
- Visual piles are derived from card-level `pileGroupId` and `pileOrder`; do not add separate persistent pile records.
- Stacks are zone piles with configurable face/default action. Library defaults to drawing; discard, banish, and hero default to opening.
- Card and stack actions should use right-click context menus and suppress the browser context menu.
- Keep hover-target action infrastructure typed, but do not bind new gameplay hotkeys without a product decision.
- Middle-mouse card zoom is hold-only, uses a fixed readable source width for all rendered card sizes, and clamps to viewport edges.

## UI Rules

- Active playtester uses full available width/height and should not add rounded outer page containers.
- Keep the lower hand/stack area above app sidebars and popovers through careful z-index choices; global app tooltips must remain above the play surface.
- Use existing theme tokens and verify both light and dark mode. The board can be more stylized than data pages, but should still respect the app theme.
- Reuse `PlaytestCard` for board, hand, opening setup, stack popovers, dragged overlays, and pile members unless there is a concrete rendering reason not to.
- Opening setup should focus on large cards, not text labels; starting mana/setup selection uses a clear border state without extra selected text.

## Checks

- Run targeted playtester tests after state or interaction changes:
  `pnpm --filter @card-reader/web test -- playtester`
- Run frontend lint and typecheck before finishing:
  `pnpm --filter @card-reader/web lint`
  `pnpm --filter @card-reader/web typecheck`
- Use the in-app browser for substantial visible interaction changes at `http://localhost:8888/playtester`.
