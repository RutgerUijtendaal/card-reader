# Card Classification Step 1.1: Authorization Seam Consolidation

Status: approved implementation plan; execute after Step 1 is merged and stable, before Step 2 begins.

This is a hardening checkpoint between the classification foundation and import inference:

1. [Card classification foundation](card-classification-step-1-foundation.md)
2. Authorization seam consolidation (this document)
3. [Import inference](card-classification-step-2-import-inference.md)
4. [Player and Game Master workspaces](card-classification-step-3-player-gm-workspaces.md)

Do not grow import or workspace behavior until this step's acceptance criteria are satisfied. The purpose is to make the existing Step 1 access boundary secure by construction before more features consume it.

## Outcome

Keep the current single entitlement decision—Game Master access initially maps to staff—but replace scattered downstream authorization booleans and repeated pool checks with one explicit card-pool visibility scope.

The API boundary converts the current user into that scope. Repositories, services, serializers, notifications, and artifact builders receive the scope or an intentionally fixed public-artifact scope. Core code remains unaware that staff is the current entitlement policy.

After this step:

- changing Game Master eligibility still requires one policy edit;
- card-derived code receives an explicit scope instead of reconstructing authorization;
- query, payload, count, sort, notification, image, replay, and artifact behavior use the same vocabulary;
- new card-derived surfaces must choose a scope before they can return data;
- Step 2 and Step 3 can reuse the seam without adding another family of authorization branches.

## Why this checkpoint exists

Step 1 correctly centralized the entitlement in `can_access_game_master_cards(user)`, but review found secondary disclosures across independent output paths: immutable images, TTS sheets, developer-data bundles, filter counts, deck filters and rules, notification snapshots, parse flags, and idempotent replay.

The post-Step-1 audit found:

- one function owns the actual staff-to-Game-Master entitlement mapping;
- four API boundary modules consume that capability directly;
- roughly fourteen non-model modules independently enforce Player/Game Master data scope across queries, serializers, notifications, validation, exports, images, TTS, and developer data.

Some distribution is unavoidable because those outputs have distinct failure domains. The problem is not multiple entitlement definitions; it is that each output currently has to remember how to translate the entitlement into safe data. This step consolidates that translation.

## Locked decisions

- `can_access_game_master_cards(user)` remains the named entitlement policy. Its initial implementation remains staff-only.
- Introduce one immutable core value object named `CardPoolScope` with a canonical set of allowed pools and an `allows_card_pool(...)` helper.
- Define canonical Player-only and all-pools scopes. Do not construct anonymous sets of pool strings throughout the codebase.
- The API auth boundary owns `card_pool_scope_for_user(user)`. It is the only user-aware mapper from entitlement to core scope.
- Core repositories and services consume `CardPoolScope`; they do not inspect users, sessions, `is_staff`, or API capability helpers.
- Public artifacts such as developer-data bundles and unauthenticated TTS sheets always use the canonical Player-only scope. They do not use the requesting user's scope.
- The current deck builder, deck validation, deck exports, and Playtester remain Player-only. A future explicit deck pool must not be inferred from contained cards.
- Direct unauthorized Game Master identities remain `404`; an unauthorized collection request that explicitly selects Game Master remains `403`. Transport status policy stays at the API boundary.
- Existing deck and group references remain intact when a card moves pools. Unauthorized payloads preserve only the already-approved restricted placeholder and generic invalid state.
- Do not add a global Django manager that silently filters every `Card` query. Administrative and migration workflows need deliberate all-pools access.
- Do not encode staff or workspace behavior in the database.

## Authoritative success condition

The step succeeds when user entitlement is translated to `CardPoolScope` once at the API boundary and every card-derived read/output path either requires that scope or declares an intentional fixed scope.

No API view, serializer, repository, or domain service outside the auth boundary may make its own staff decision. No first-party payload builder may accept an `allow_game_master_cards: bool` flag. Preserving current endpoint behavior and passing the complete authorization matrix are authoritative; the presence of the new type alone is not.

## Target architecture

### Core scope

Place `CardPoolScope` beside the code-owned card-pool domain types so repositories can depend on it without importing API or service-layer modules.

The type owns only data visibility:

```python
@dataclass(frozen=True)
class CardPoolScope:
    allowed_pools: frozenset[CardPool]

    def allows_card_pool(self, card_pool: str) -> bool: ...
```

Expose canonical constants or constructors for:

- Player-only scope;
- all supported pools.

Validate and normalize pool values when constructing the scope. Do not add user, staff, role, request, or route state to this core type.

### API entitlement mapper

Keep `can_access_game_master_cards(user)` in `card_reader_api.common.auth_access` and add:

```python
def card_pool_scope_for_user(user: object) -> CardPoolScope: ...
```

The mapper returns all pools when the capability is present and Player-only otherwise. Session capabilities continue to expose `can_access_game_master_cards` for frontend feature detection.

Views obtain the scope once per request and pass it downward. Views may use `scope.allows_card_pool(...)` to choose the established `403` or `404` transport response, but must not recreate the staff policy.

### Scoped repositories

Every repository entry point used by a card-derived HTTP or publication surface must accept an explicit scope or an explicit selected pool already proven to be within that scope.

Cover at least:

- card lists, details, generations, and images;
- grouped cards and group members;
- linked-card counts, previews, and sort popularity;
- deck search predicates and embedded card loading;
- exports and selectors;
- immutable image ownership resolution;
- TTS reconciliation and rendering inputs;
- developer-data selection and export.

Filter restricted rows before applying search, ordering, counts, annotations, validation, or aggregation. Redacting after a query is not sufficient because result membership and order can become an oracle.

Keep unrestricted persistence helpers available only where their ownership requires it. Give scoped read functions names and signatures that make omission difficult; do not add permissive default scopes to public-facing repository APIs.

### Scoped presentation

Replace `allow_game_master_cards: bool` parameters with `card_pool_scope: CardPoolScope` in card-derived payload builders.

Provide shared helpers for:

- deciding whether a card may be embedded;
- building the canonical restricted summary/full-card placeholder;
- building generic restricted-reference invalid state;
- selecting only visible cards before calculating rules, warnings, counts, or totals that could expose restricted configuration.

Card, group, catalog, deck, notification, and export serializers should compose those helpers rather than inventing feature-specific redaction copy or shapes.

### Stateful and generated outputs

Treat durable and generated outputs as separate authorization failure domains:

- archive card-linked notification rows when a Player card becomes Game Master;
- suppress current Player-workspace notification events for Game Master cards;
- reject capability-unsafe idempotent replay without returning embedded restricted references;
- invalidate or rerender public TTS material after a pool transition;
- keep developer-data and public TTS generation fixed to Player-only scope;
- authorize immutable shared image bytes when at least one owning card is visible in the supplied scope.

Central scope vocabulary must be shared, but cleanup and failure semantics remain owned by each workflow. A cleanup failure must not reverse a successfully persisted classification edit; it must leave the derived surface unavailable until reconciliation succeeds.

## Implementation sequence

1. Capture the current authorization behavior as a surface matrix before refactoring.
2. Add `CardPoolScope`, canonical scopes, normalization tests, and `card_pool_scope_for_user(user)`.
3. Refactor API card, group, deck, and export views to create one request scope and pass it downward.
4. Refactor card/group/catalog repositories so filtering occurs before search, counts, sorting, previews, or aggregation.
5. Replace embedded-payload authorization booleans with scoped presentation helpers, including safe deck-derived validation and rules.
6. Move notification, image, TTS, developer-data, and replay paths onto the same scope vocabulary while preserving their independent cleanup semantics.
7. Remove obsolete `allow_game_master_cards` parameters and duplicate pool-access branches.
8. Add architecture guards that prevent new direct staff checks or boolean Game Master presentation flags outside the auth boundary.
9. Update current-state access, card, deck, notification, developer-data, and TTS documentation where implementation details changed.
10. Run all permitted validation and complete a final surface audit before starting Step 2.

## Required authorization matrix

For every applicable surface, test anonymous, authenticated non-staff, and staff viewers against Player and Game Master cards.

The matrix must cover:

- list membership, pagination counts, filters, ordering, and grouped gallery;
- direct card/version/generation lookup;
- current, historical, immutable, and shared-byte images;
- card groups, catalog previews, suggestion occurrences, and linked counts;
- deck lists, filters, details, validation, effective rules, creation, updates, and idempotent replay;
- Playtester selection and direct initialization eligibility;
- parse-flag creation and review notifications;
- notification list, unread count, and pool-transition retirement;
- CSV, TTS, deck, gallery, and content-version exports;
- TTS sheet reconciliation, stale-atlas denial, and rerendering;
- developer-data selection, publication validation, grants, and downloads;
- Player-to-Game-Master and Game-Master-to-Player transitions with existing deck/group references.

Assert both positive access and non-disclosure. Non-disclosure includes identity, labels, metadata, roles, configuration, counts, ordering effects, validation copy, target URLs, persistent snapshots, and generated bytes.

## Architecture guards

Add focused source-boundary tests or lint checks that fail when:

- card-classification code outside `card_reader_api.common.auth_access` reads `user.is_staff` directly;
- a first-party card-derived payload builder adds an `allow_game_master_cards` boolean;
- public developer-data or TTS code requests the all-pools scope;
- secure API entry points call an unrestricted card lookup before applying the request scope.

Keep these guards narrow enough to permit unrelated staff-only admin features. They protect the classification seam, not every authorization rule in the repository.

## Validation

Do not run prohibited service/integration suites locally. Add the backend regression tests for CI, then run repository-approved static and frontend checks locally:

```text
pnpm --filter @card-reader/core lint
pnpm --filter @card-reader/core typecheck
pnpm --filter @card-reader/api lint
pnpm --filter @card-reader/api typecheck
pnpm --filter @card-reader/web lint
pnpm --filter @card-reader/web typecheck
pnpm --filter @card-reader/web test -- <affected specs>
uv run --project ../.. --package card-reader-api python manage.py check
```

Also validate the authorization matrix in CI and manually inspect representative Player and Game Master UI states in light and dark themes when visible presentation code changes.

## Acceptance criteria

- `can_access_game_master_cards(user)` remains the only staff-to-Game-Master entitlement definition.
- `card_pool_scope_for_user(user)` is the only user-aware translation into core data scope.
- Core code does not import API auth helpers or inspect users to decide card visibility.
- Public-facing card-derived repository and payload APIs require an explicit scope or a previously validated selected pool.
- No first-party `allow_game_master_cards` payload parameter remains.
- Search, counts, ordering, validation, rules, notifications, replay, images, exports, TTS, and developer-data cannot expose out-of-scope card data.
- Public derived artifacts remain Player-only regardless of which users receive the Game Master capability.
- Current `403`, `404`, restricted-placeholder, reference-preservation, and invalid-state behavior remains compatible.
- The authorization matrix passes for anonymous, authenticated non-staff, and staff viewers.
- Architecture guards prevent the seam from scattering again.
- Lint, typecheck, Django checks, affected frontend tests, CI backend tests, and documentation validation pass.

## Explicit non-goals

- Changing Game Master eligibility from staff.
- Adding roles, permissions, object-level grants, or a policy engine.
- Adding the Player/Game Master sidenav toggle.
- Import inference or batch classification controls.
- Persisting deck pools or designing Game Master decks.
- Scenario persistence or Game Master Playtester behavior.
- Replacing Django authentication, sessions, or CSRF behavior.
- Adding a global filtered `Card` manager.
