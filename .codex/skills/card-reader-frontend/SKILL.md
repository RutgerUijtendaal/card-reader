---
name: card-reader-frontend
description: Work on the Card Reader Vue frontend for gallery, review, imports, settings, auth, and shared UI behavior. Use when changing frontend pages, composables, routing, API client usage, filter behavior, theming, or visible UI in this repository.
---

# Card Reader Frontend

Follow `AGENTS.md` first. Use this skill both when implementing frontend changes and when reviewing them. Add `card-reader-classification`, `card-reader-developer-data`, `card-reader-notifications`, `card-reader-playtester`, or `card-reader-tts` when a change enters one of those specialized workflows.

## Core Rules

- Preserve the Vue 3 + TypeScript + Vite behavior while using the four frontend layers: `app`, `features`, `domain`, and `shared`.
- Classify by ownership before adding a file: global orchestration goes in `app`; one-workflow business code in `features/<name>`; cross-workflow business code in `domain/<name>`; domain-agnostic reuse in `shared`.
- Respect the enforced dependency direction: `app` may depend on every layer; a feature may depend on itself, domain, and shared; a domain may depend on shared and only the domain slices allowlisted in `frontend/eslint.config.js`; shared may depend only on shared. Never import from another feature or create a domain cycle.
- Use direct file imports. Do not add barrel files or transitional re-exports to mask ownership.
- Keep reusable card queries, filters, gallery behavior, sorting, symbols, preferences, and card UI in `frontend/src/domain/cards`.
- Keep reusable deck contracts, clients, constraints, calculations, exports, route helpers, tags, and deck UI in `frontend/src/domain/decks`; use `frontend/src/domain/deck-building` for contracts shared with cards.
- Keep app bootstrap, routing, shell navigation/hotkeys, theme orchestration, and global styles in `frontend/src/app`.
- Keep icons consistent across matching sidebar links and page headers. Source stable section icons from `frontend/src/shared/components/app/appSectionIcons.ts`, and pool-aware Gallery icons from the cards-domain pool icon mapping; never import separate icons for the two surfaces.
- Keep generic API infrastructure, form/modal/layout controls, floating UI, keyboard/pointer helpers, and generic composables in `frontend/src/shared`.
- Keep Axios calls in the focused `api.ts` or `api/*` client owned by the relevant feature or domain. Pages, components, stores, and workflow composables consume typed client functions instead of the shared Axios instance.
- Co-locate unit and component specs with their source. Use a feature `tests/` directory only for scenarios spanning several source files.
- Use shared deck list components and `DeckListRecord`-compatible props for deck listing surfaces that can consume either full or summary deck records.
- Prefer deck summary endpoints and `DeckSummaryRecord` for list/selector views that do not need full card entries; fetch full `DeckRecord` only for detail/editor/export/playtest flows that need complete deck contents.
- Keep feature roots limited to pages/views and true feature entry files such as private `api.ts`, `types.ts`, or stores. Put implementation details under `components`, `composables`, or `utils`.
- Deck-building rule defaults and example config are backend-owned through `GET /decks/rules`; use the shared deck rules client/fallback instead of duplicating rule constants in feature UI.
- In the card detail editor, keep card-level controls on the `Card` tab and version-level controls on the `Card Version` tab.
- Use `JsonEditorField` for deck-building config JSON so formatting, validation affordances, and examples stay consistent with other admin JSON inputs.
- For routed app pages with filters, local navigation, summaries, or page controls, prefer the shared `AppPageLayout` and `AppStickyAside` structure.
- Routed pages that fetch initial page data should expose a full, layout-shaped skeleton loading state instead of falling through to empty states or text-only loading labels.
- Primary page lists and content should use the shell page scroll; avoid max-height primary list containers that trap content.
- Desktop asides should behave as edge-attached side panels below the lifted shell header, use the shared aside width, keep bounded inner scrolling only inside the aside, and place persistent footer controls in the shared footer slot so they anchor at the bottom.
- Mobile page layouts should stack aside content above main content in natural page flow.
- Preserve and extend the shared theme/token system in the ordered `frontend/src/app/styles.css` entrypoint, its `styles/base.css`, `styles/components.css`, and `styles/utilities.css` layer files, and `frontend/src/shared/composables/useTheme.ts`.
- Prefer semantic theme primitives and shared classes over ad hoc color styling.
- Avoid overusing containers and card shells. Prefer letting controls and content float on the app background when hierarchy remains clear, using dividers, spacing, accent lines, and selected states for visual separation between sections.
- Keep user-facing page and section descriptions focused on the enduring purpose and end result of the screen; avoid copy that calls out specific implementation details, temporary workflow mechanics, or design decisions that may look out of place as the page grows.
- Verify visible UI in both light and dark modes.
- Treat Player, Evil, and Neutral card data as equally public. Do not model pool entitlements or redact card payloads by viewer.
- Treat the selected pool as ordinary workspace context only. Admin and Review remain global, and new imports must start without inherited pool or template defaults.
- Keep Gallery facet visibility, hidden-state sanitation, and pool-scoped catalog reconciliation in the cards-domain Gallery policy; do not leak that policy into Admin, Review, or purpose-specific deck filters.
- Model multi-phase workflows with tagged states rather than overlapping booleans, and cover their allowed transition table with tests.
- When an uncertain state includes active reconciliation and a later user-decision phase, encode that phase in the tagged state so route guards block only while background completion may still navigate.
- Capture an immutable request payload and idempotency key before uncertain mutations; retries must reuse both exactly.
- Enter the mutation-locked request state before awaiting persistence of an immutable attempt, and coalesce repeated actions while that sealing write waits. An explicit retry of an already captured attempt may continue when best-effort persistence is conflict-paused, but it must remain non-navigable unless the exact attempt is durable.
- Treat browser persistence, server mutation, and cleanup as independent failure domains. Confirmed server success is terminal even when local cleanup fails.
- Catch request failures only around the request itself. Post-success routing, callbacks, or cleanup errors must not re-enter request reconciliation or replace confirmed success with an uncertain state.
- If terminal-success navigation can fail, retain a single-flight navigation retry that never repeats the server mutation. Keep mutations locked until navigation succeeds while leaving only that retry action available.
- Run authoritative pending-request reconciliation even when auxiliary recovery work such as filters, snapshots, or metadata hydration fails; those failures must not unlock mutation first.
- Block route leave while a recovered pending request is still hydrating, so its later reconciliation cannot route from an abandoned component.
- A lookup miss is definitive only when paired with authoritative evidence that the originating mutation failed. The presence of an HTTP response is insufficient: gateway errors and request timeouts can race an upstream commit. On reload, timeout-only misses must retain the immutable pending request for idempotent retry.
- Use revision-conditional writes plus native storage events for cross-tab state. A `localStorage` read followed by a write is not atomic; serialize the comparison and mutation with Web Locks or use a transactional persistence primitive, falling back to memory-only when atomicity is unavailable. Pause mutation and require an explicit conflict resolution instead of silently choosing a source of truth.
- Keep persistence capability consistent across reads and writes: do not offer recovery from a storage backend when the locks or transactions required to mutate that recovered state are unavailable.
- Memory-only persistence must keep probing on later saves; content equality is not a no-op while the latest state is not durable.
- For queued destructive actions and explicit conflict resolutions, preserve the decision-time revision or re-check conflict state inside the queued callback. Never derive permission from a newer remote revision observed while waiting.
- Bind destructive confirmations to the state that opened them and close them when a conflict replaces that state. Never overwrite a remote draft while it contains an unresolved immutable request.
- Recovery and cross-tab conflict UI must be mutually exclusive. If a conflict interrupts recovery, preserve the recovered draft as the local conflict candidate before closing the recovery decision surface.
- Keep local retirement knowledge separate from the currently observed storage slot. Once a tab learns that its draft key was created elsewhere, preserve that fact through later slot changes so Keep assigns a fresh key, but always derive the visible conflict and overwrite preconditions from the latest slot.
- Before routing from a retirement marker, resolve its creation key against the server. A deleted outcome must preserve the local contents under a fresh key instead of navigating to a stale resource.
- Allow an unresolved request to leave only when its exact immutable key and payload are durably recoverable. Memory-only or conflict-displaced attempts must remain on the page until resolved.

## Implementation Workflow

1. Inspect the surrounding feature area before editing.
2. Apply the ownership test and choose `app`, the owning feature, an existing domain, or `shared` before creating a file.
3. Check the owning domain API client, composables, components, and utilities before adding parallel behavior.
4. Keep feature pages focused on workflow behavior such as navigation, pagination, editor state, and local interactions.
5. Promote business code to a domain only when multiple workflows consume it; keep generic-looking one-off code feature-local until reuse exists.
6. When a second workflow needs feature-owned code, move it atomically to the right domain or shared owner and update all consumers; never import feature-to-feature.
7. If the change touches deck list or selector pages, decide explicitly whether summary records are sufficient before requesting full deck records.
8. If the change touches card filters or gallery state, inspect `frontend/src/domain/cards` first. Keep normalization in `cardFilterState.ts`, route serialization in `cardFilterRouteState.ts`, catalog/id translation in `cardFilterSelection.ts`, and API payloads in `cardFilterRequest.ts`.
9. If the change touches deck-building constraints, load defaults/examples from the backend metadata endpoint and keep frontend fallbacks covered by tests.
10. If the change touches a routed page with initial data fetching, preserve or add a page-shaped skeleton that matches the loaded layout.
11. If the change touches visible UI, preserve token-backed theme behavior and verify both light and dark modes.
12. If the change touches workspace or pool state, test direct navigation, anonymous access, rapid workspace changes, and global Admin/Review behavior as applicable.
13. Co-locate affected specs, then run targeted tests, lint, and typecheck; run the build when entrypoints, routing, aliases, or lint configuration change.

## Review Focus

- Feature-to-feature imports or imports against the `app -> features -> domain -> shared` direction
- Cross-workflow business logic left inside a feature after another workflow consumes it
- Domain-agnostic code placed in a business domain, or speculative reuse promoted too early
- Full deck records fetched for list-only surfaces where summary records would preserve payload boundaries
- Card/filter API reads or filter logic duplicated outside `frontend/src/domain/cards`
- New helpers added when an existing composable or shared utility already fit
- Feature pages taking on reusable domain state, API, or parsing responsibilities
- Direct Axios calls outside focused feature/domain API clients or shared API infrastructure
- Specs separated from their source without being a genuine multi-file scenario
- Card/deck or other circular domain ownership
- Domain imports not represented in the validated acyclic allowlist in `frontend/eslint.config.js`
- Page layouts that reintroduce max-height primary list containers instead of using shell page scroll with sticky/bounded asides
- Routed pages that show empty states, partial controls, or text-only loading while initial page data is still loading
- Theme drift from raw colors, light-only assumptions, or component-local styling systems
- Sidebar and page-header icons that represent the same section but do not consume the same shared icon definition
- Unnecessary framed containers where divider-separated, background-floating content would be clearer and more consistent
- UI changes verified in one theme only
- Missing validation for touched frontend behavior
- Flag combinations that encode hidden workflow phases, mutable retry payloads, cleanup that gates confirmed success, or tabs that silently overwrite storage
- Deck-building defaults or example JSON copied into UI code without a backend metadata source or fallback test
- Pool entitlement fields, viewer-dependent card redaction, or global staff screens accidentally scoped by workspace
- Hidden Gallery filter state surviving in routes or requests, or failed catalog loads erasing selections

## File Hotspots

- `frontend/src/app`
- `frontend/src/app/router`
- `frontend/src/app/styles.css`
- `frontend/src/app/styles/base.css`
- `frontend/src/app/styles/components.css`
- `frontend/src/app/styles/utilities.css`
- `frontend/src/features`
- `frontend/src/domain/cards`
- `frontend/src/domain/decks`
- `frontend/src/domain/session`
- `frontend/src/domain/notifications`
- `frontend/src/shared`
- `frontend/eslint.config.js`

## Avoid

- Re-implementing card/filter API reads, parsing, or filter-param building outside `frontend/src/domain/cards`
- Calling the shared Axios instance directly from a page, component, store, or workflow composable
- Importing from another feature; extract the genuinely shared responsibility to a domain or shared owner
- Letting feature roots accumulate helpers or implementation details that belong in their private subfolders
- Adding re-export shims, barrels, or aliases that preserve obsolete paths
- Scattering raw light-only or dark-only classes through feature components
- Adding card or panel shells for every section when dividers, spacing, and selected states provide enough structure
- Adding dependencies before checking whether the repo already has a clean fit
- Introducing a parallel component or styling system for a one-off feature
- Building routed app pages with bespoke aside widths, ad hoc sticky offsets, or primary list inner scrollers instead of the shared `AppPageLayout` and `AppStickyAside` structure
