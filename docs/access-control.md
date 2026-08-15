# Access Control

Card Reader combines public browsing with session-authenticated management tools. Backend capabilities are the source of truth; the frontend uses the session capability payload to decide which navigation and actions to show.

## Authentication and sessions

The web application uses Django session authentication. Login and session responses include a CSRF token, and unsafe browser requests require CSRF protection.

Inactive users cannot authenticate or continue using protected capabilities. The central authenticated-user predicate includes active status, so an existing session whose account becomes inactive is reported as unauthenticated, loses staff and other protected capabilities, and receives only the public Player card scope. Sensitive token-based flows also re-check the issuing account instead of assuming that access remains valid for the token's entire lifetime.

## Access levels

The main access levels are:

- Public visitors can browse Player-card and public deck surfaces and load their public card and symbol assets.
- Active authenticated users can use account-scoped features and other capabilities granted to ordinary members.
- Staff users can access administrative workflows including imports, review, catalogs, templates, exports, user management, and developer-data publishing.
- Admin and Review use the staff user's complete authorized card-pool scope; changing the shell workspace never narrows their catalogs, previews, counts, or queues. Imports may use the workspace only as an explicit, editable default.
- Superusers can access maintenance operations and the most sensitive administrative views.
- Developer users can download developer-data bundles even when they are not staff. Staff receive this capability automatically.

The developer flag is deliberately narrower than staff access: it supports project onboarding without granting import, catalog, user-management, or maintenance permissions. See [Developer data](developer-data.md) for its download and publishing flows.

## Restricted card pools

Player is the public/default card pool. Evil and Neutral are separate restricted pools whose current policy grants access to staff only. At the API boundary, `card_pool_scope_for_user` is the single policy seam that translates a user into an immutable core `CardPoolScope`: ordinary and anonymous viewers receive the canonical Player-only scope, while staff receive Player, Evil, and Neutral. Core repositories, services, and payload builders consume the scope without inspecting users or staff state, so changing the entitlement policy remains a single boundary edit.

An unauthorized collection request that explicitly selects Evil or Neutral returns `403` with generic restricted-pool copy. Direct restricted card, version, image, and immutable-asset lookups return `404` so they do not disclose whether an identity exists. The same policy applies to grouped cards, exports, selectors, filter counts, and other card-derived public data. If a Player card already referenced by an ordinary user's deck is reclassified, the deck reference and invalid-state warning remain, but the embedded restricted card content and image are replaced by a generic placeholder. Deck rules and validation details returned to that owner are computed from visible Player cards or replaced with a generic restricted-card issue, so restricted card configuration and type behavior are not exposed indirectly.

Developer-data bundles remain fixed Player-only public artifacts. Persistent TTS sheets are instead
partitioned by card pool: Player sheets are public, while Evil and Neutral sheets require either the
normal restricted-pool session scope or a signed export capability for one exact rendered sheet
revision. Gallery and content-version TTS exports created by staff can therefore contain cards from
any authorized pool without making restricted sheets generally public. The capability is bound to
the sheet id and rendered checksum, so it cannot load another sheet or a later rerender; direct
unauthorized requests retain the generic `404` boundary. Deck TTS exports remain Player-only because
decks are currently a Player workflow, not because TTS cards have a Player-only format.

Card-derived search, counts, ordering, validation, previews, notifications, and generated outputs apply their scope before exposing results. Direct restricted identities still use the established `404` policy, while an explicitly forbidden Evil or Neutral collection selection remains `403`.

## Capability-driven UI

The authenticated session payload exposes named capabilities plus ordered `accessible_card_pools`. Ordinary sessions receive `player`; staff sessions receive `player`, `evil`, and `neutral`. The global sidenav workspace consumes this list instead of duplicating pool literals or staff checks in the frontend. It shows only permitted pools, restores only a permitted preference, and falls back to Player for logged-out or reduced-scope sessions.

Workspace state is navigation context rather than authorization. Voluntary selection uses one typed route-capability policy: global routes stay mounted, Gallery replaces only its pool-owned state, resource routes retain the opened identity and update their return context, and Player-only routes fall back only when the selected pool is incompatible. Route-changing selections commit after navigation is accepted, so a leave guard or superseding selection cannot partially change the stored context. Session identity or pool-scope loss remains stricter: it increments the frontend request generation synchronously, discards restricted card collections and filter metadata, removes disallowed route state, and forces mounted card and group resources to clear and revalidate against the new scope. Late collection and resource responses from the previous generation are ignored. Direct backend authorization remains authoritative throughout every transition.

The server still authorizes every request. Hiding an unavailable control improves the interface but is never treated as the security boundary.

## Managed users

Staff can manage application users through the admin-facing user tools. Supported lifecycle operations include creating users, changing appropriate roles, deactivating or restoring access, resetting password setup, and toggling developer access.

Managed and unmanaged accounts are distinguished so the application does not accidentally claim ownership of accounts provisioned through another process. Deactivation is preferred over deletion when history or ownership relationships must remain intact.

## Access requests

The access-request workflow allows a prospective user to request an account without exposing account creation publicly. Staff review the request, create the managed user when approved, and provide the password-setup link through an appropriate out-of-band channel.

Requests and staff actions remain auditable. Approval does not bypass normal active-user, session, or capability checks.

## Operational principles

- Authorize at the API boundary and enforce domain-sensitive rules in core services.
- Prefer explicit capabilities for features that do not map cleanly to the full staff role.
- Preserve ownership and audit history when access is revoked.
- Re-check active status for long-lived or bearer-token workflows.
- Keep credentials and local user seed files out of committed source.
