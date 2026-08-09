---
name: card-reader-review
description: Review changes in the Card Reader monorepo with a bug-finding mindset. Use when asked to review code, assess regressions, check architectural fit, or identify missing tests and risks in this repository.
---

# Card Reader Review

Follow `AGENTS.md` first. Use this skill when reviewing pull requests, local diffs, or proposed designs. Prioritize findings over summaries and focus on bugs, regressions, architectural drift, and missing validation.

## Review Priorities

- Service-boundary violations between `api`, `parser`, and `core`
- Schema ownership mistakes outside `services/core`
- Core layering drift: transport logic in repositories, Django query/write details in services, or domain workflows in API views
- New one-off modules in `card_reader_core` root or legacy `*_repository.py` files instead of feature packages
- Frontend dependency drift against the enforced layers and validated domain allowlist, especially feature-to-feature imports, shared/domain upward imports, unapproved cross-domain edges, or cycles
- Card filter and gallery logic drift outside `frontend/src/domain/cards`, including duplicated API reads or route/request/id-translation logic placed in the wrong focused filter file
- Direct Axios calls from pages, components, stores, or workflow composables instead of focused feature/domain API clients
- Circular ownership between frontend domains, especially cards and decks
- Deck list/query regressions where list surfaces fetch full deck records instead of summary records without needing full entries
- Playtester route regressions around `/playtester` versus `/playtester/:deckId`, local draft preservation, preview-start behavior, card scale preference, or hotkey/help alignment
- Playtester state ownership regressions that blur core, board, opening, and draft-persistence modules or reintroduce an aggregate façade
- Theme/token drift or light/dark regressions in visible frontend changes
- Auth regressions around public vs staff/superuser behavior
- Import pipeline regressions in async job creation, claiming, and persistence
- Missing lint, typing, or test coverage for touched behavior
- Stateful workflows encoded as interacting flags without an explicit transition model
- Cleanup failures that block or undo an already confirmed authoritative success
- Background reconciliation that can navigate after route leave, or auxiliary recovery failures that unlock an unresolved authoritative request
- Reload recovery that treats repeated lookup misses as proof of mutation failure without a definitive response from the originating request
- Ambiguous network responses without idempotent lookup/retry behavior, retries whose key or payload can change, or used keys that become reusable when their created resource is deleted
- Local and server sources of truth that can silently drift, especially across tabs or after partial persistence failures
- Recovery and conflict prompts that can overlap, or conflict resolution that substitutes an unhydrated blank form for the recoverable local candidate
- Conditional browser writes implemented as a non-atomic read-then-write instead of a cross-tab lock or transactional primitive

## Review Workflow

1. Read the changed files in context, not in isolation.
2. Infer the intended change, then compare that intent to the actual diff and surrounding code paths.
3. Look for behavioral regressions before style issues.
4. Check that backend changes preserve the controller -> service -> repository boundary.
5. Prefer concrete findings with file references and impact.
6. Call out missing tests when a regression risk is not otherwise covered.
7. Treat lint and typecheck as baseline, not as substitutes for code review.
8. Keep summaries brief and secondary.

## Implementation Follow-Through

- If review feedback suggests code changes, preserve the same review standards while implementing the fix.
- Fix the underlying issue rather than muting the symptom.
- Re-check nearby boundaries after making the fix so the patch does not introduce a different regression.

## Avoid

- Treating naming preferences as findings unless they hide a real maintenance risk
- Approving architecture drift because the local patch is small
- Replacing concrete findings with generic praise or summaries
