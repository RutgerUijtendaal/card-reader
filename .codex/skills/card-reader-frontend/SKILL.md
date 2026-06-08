---
name: card-reader-frontend
description: Work on the Card Reader Vue frontend for gallery, review, imports, settings, auth, and shared UI behavior. Use when changing frontend pages, composables, routing, API client usage, filter behavior, theming, or visible UI in this repository.
---

# Card Reader Frontend

Follow `AGENTS.md` first. Use this skill both when implementing frontend changes and when reviewing them. It should help place code correctly and preserve the repo's existing UI and state patterns.

## Core Rules

- Preserve the existing Vue 3 + TypeScript + Vite structure.
- Check for existing shared utilities, composables, and modules before adding new helpers.
- Keep shared frontend logic in `frontend/src/composables`, using domain subfolders when the shared behavior has a clear owner.
- Keep shared card filter behavior in `frontend/src/composables/card-filters`.
- Keep shared gallery/search behavior in `frontend/src/composables/card-gallery` or root composables such as `useCardCollection`, `useGalleryOptions`, and preference composables.
- Keep shared Vue components in `frontend/src/components`; if more than one module consumes a component, promote it out of the feature module.
- Keep feature module roots limited to pages/views plus core module files such as `api.ts`, `types.ts`, and stores. Put module implementation details under `components`, `composables`, `utils`, or `tests`.
- Deck-building rule defaults and example config are backend-owned through `GET /decks/rules`; use the shared deck rules client/fallback instead of duplicating rule constants in feature UI.
- In the card detail editor, keep card-level controls on the `Card` tab and version-level controls on the `Card Version` tab.
- Use `JsonEditorField` for deck-building config JSON so formatting, validation affordances, and examples stay consistent with other admin JSON inputs.
- For full-page application views, prefer inner scrolling within the main content segments instead of making the entire page scroll; match the layout behavior used by the current settings and deck builder pages.
- Preserve and extend the shared theme/token system in `frontend/src/styles.css` and `frontend/src/composables/useTheme.ts`.
- Prefer semantic theme primitives and shared classes over ad hoc color styling.
- Avoid overusing containers and card shells. Prefer letting controls and content float on the app background when hierarchy remains clear, using dividers, spacing, accent lines, and selected states for visual separation between sections.
- Keep user-facing page and section descriptions focused on the enduring purpose and end result of the screen; avoid copy that calls out specific implementation details, temporary workflow mechanics, or design decisions that may look out of place as the page grows.
- Verify visible UI in both light and dark modes.

## Implementation Workflow

1. Inspect the surrounding feature area before editing.
2. Check whether the change belongs in a page, module-owned component/composable/util, root shared component, root shared composable, or existing library helper before creating new files.
3. Reuse existing API client patterns, composables, and UI utilities when they fit.
4. Keep page modules focused on page behavior like navigation, pagination, and local interaction flow.
5. Move reusable state, parsing, transformation, export, route, or preference logic into `frontend/src/composables` only when reuse is real.
6. If a component becomes cross-module, move it to `frontend/src/components` before wiring the second module to it.
7. If the change touches filters, inspect `frontend/src/composables/card-filters` first and extend it there instead of cloning the logic into a page.
8. If the change touches deck-building constraints, load defaults/examples from the backend metadata endpoint and keep frontend fallbacks covered by tests.
9. If the change touches visible UI, preserve token-backed theme behavior and verify both light and dark modes.
10. Run lint and typecheck before finishing.

## Review Focus

- Shared logic left inside a feature module after it is consumed by another module
- Shared components left inside feature module `components` folders after cross-module reuse appears
- Filter logic duplicated outside `frontend/src/composables/card-filters`
- New helpers added when an existing composable or shared utility already fit
- Page modules taking on shared state or parsing responsibilities
- Module root files that should be under `components`, `composables`, `utils`, or `tests`
- Full-page layouts that scroll the entire page instead of keeping page chrome stable and giving the main segments their own scroll areas
- Theme drift from raw colors, light-only assumptions, or component-local styling systems
- Unnecessary framed containers where divider-separated, background-floating content would be clearer and more consistent
- UI changes verified in one theme only
- Missing validation for touched frontend behavior
- Deck-building defaults or example JSON copied into UI code without a backend metadata source or fallback test

## File Hotspots

- `frontend/src/composables`
- `frontend/src/composables/card-filters`
- `frontend/src/composables/card-gallery`
- `frontend/src/components`
- `frontend/src/styles.css`
- `frontend/src/lib`
- `frontend/src/pages`

## Avoid

- Re-implementing filter parsing or API filter param building outside `frontend/src/composables/card-filters`
- Importing from another module's `components`, `composables`, or `utils` folders; promote genuinely shared code to root `components` or `composables`
- Letting feature module roots accumulate helpers, specs, or implementation details that belong in subfolders
- Scattering raw light-only or dark-only classes through feature components
- Adding card or panel shells for every section when dividers, spacing, and selected states provide enough structure
- Adding dependencies before checking whether the repo already has a clean fit
- Introducing a parallel component or styling system for a one-off feature
- Building new application pages around document-style full-page scrolling when segmented inner scrolling is the established pattern
