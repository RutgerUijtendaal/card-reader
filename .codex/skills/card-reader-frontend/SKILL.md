---
name: card-reader-frontend
description: Work on the Card Reader Vue frontend for gallery, review, imports, settings, auth, and shared UI behavior. Use when changing frontend pages, composables, routing, API client usage, filter behavior, theming, or visible UI in this repository.
---

# Card Reader Frontend

Follow `AGENTS.md` first. Use this skill both when implementing frontend changes and when reviewing them. It should help place code correctly and preserve the repo's existing UI and state patterns.

## Core Rules

- Preserve the existing Vue 3 + TypeScript + Vite structure.
- Check for existing shared utilities, composables, and modules before adding new helpers.
- Keep shared card filter behavior in `frontend/src/modules/card-filters`.
- For full-page application views, prefer inner scrolling within the main content segments instead of making the entire page scroll; match the layout behavior used by the current settings and deck builder pages.
- Preserve and extend the shared theme/token system in `frontend/src/styles.css` and `frontend/src/composables/useTheme.ts`.
- Prefer semantic theme primitives and shared classes over ad hoc color styling.
- Keep user-facing page and section descriptions focused on the enduring purpose and end result of the screen; avoid copy that calls out specific implementation details, temporary workflow mechanics, or design decisions that may look out of place as the page grows.
- Verify visible UI in both light and dark modes.

## Implementation Workflow

1. Inspect the surrounding feature area before editing.
2. Check whether the change belongs in a page, shared composable, shared module, or existing library helper before creating new files.
3. Reuse existing API client patterns, composables, and UI utilities when they fit.
4. Keep page modules focused on page behavior like navigation, pagination, and local interaction flow.
5. Move reusable state, parsing, or transformation logic into existing shared locations only when reuse is real.
6. If the change touches filters, inspect `frontend/src/modules/card-filters` first and extend it there instead of cloning the logic into a page.
7. If the change touches visible UI, preserve token-backed theme behavior and verify both light and dark modes.
8. Run lint and typecheck before finishing.

## Review Focus

- Filter logic duplicated outside `frontend/src/modules/card-filters`
- New helpers added when an existing composable or shared utility already fit
- Page modules taking on shared state or parsing responsibilities
- Full-page layouts that scroll the entire page instead of keeping page chrome stable and giving the main segments their own scroll areas
- Theme drift from raw colors, light-only assumptions, or component-local styling systems
- UI changes verified in one theme only
- Missing validation for touched frontend behavior

## File Hotspots

- `frontend/src/modules/card-filters`
- `frontend/src/composables`
- `frontend/src/styles.css`
- `frontend/src/lib`
- `frontend/src/pages`

## Avoid

- Re-implementing filter parsing or API filter param building outside `card-filters`
- Scattering raw light-only or dark-only classes through feature components
- Adding dependencies before checking whether the repo already has a clean fit
- Introducing a parallel component or styling system for a one-off feature
- Building new application pages around document-style full-page scrolling when segmented inner scrolling is the established pattern
