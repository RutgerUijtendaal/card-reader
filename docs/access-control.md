# Access Control

Card Reader combines public browsing with session-authenticated management tools. Backend capabilities are the source of truth; the frontend uses the session capability payload to decide which navigation and actions to show.

## Authentication and sessions

The web application uses Django session authentication. Login and session responses include a CSRF token, and unsafe browser requests require CSRF protection.

Inactive users cannot authenticate or continue using protected capabilities. Sensitive token-based flows also re-check the issuing account instead of assuming that access remains valid for the token's entire lifetime.

## Access levels

The main access levels are:

- Public visitors can browse Player-card and public deck surfaces and load their public card and symbol assets.
- Active authenticated users can use account-scoped features and other capabilities granted to ordinary members.
- Staff users can access administrative workflows including imports, review, catalogs, templates, exports, user management, and developer-data publishing.
- Superusers can access maintenance operations and the most sensitive administrative views.
- Developer users can download developer-data bundles even when they are not staff. Staff receive this capability automatically.

The developer flag is deliberately narrower than staff access: it supports project onboarding without granting import, catalog, user-management, or maintenance permissions. See [Developer data](developer-data.md) for its download and publishing flows.

## Game Master cards

Game Master card access is represented by the named `can_access_game_master_cards` capability. Its current policy grants access to staff only. At the API boundary, `card_pool_scope_for_user` translates that entitlement into the immutable core `CardPoolScope`: ordinary and anonymous viewers receive the canonical Player-only scope, while entitled viewers receive the canonical all-pools scope. Core repositories, services, and payload builders consume the scope without inspecting users or staff state, so changing the entitlement policy remains a single boundary edit.

An unauthorized collection request that explicitly selects the Game Master pool returns `403`. Direct Game Master card, version, image, and immutable-asset lookups return `404` so they do not disclose whether an identity exists. The same policy applies to grouped cards, exports, selectors, filter counts, and other card-derived public data. If a Player card already referenced by an ordinary user's deck is reclassified, the deck reference and invalid-state warning remain, but the embedded Game Master card content and image are replaced by a restricted placeholder. Deck rules and validation details returned to that owner are computed from visible Player cards or replaced with a generic restricted-card issue, so restricted card configuration and type behavior are not exposed indirectly.

Unauthenticated TTS sheets and developer-data bundles are public derived artifacts and therefore
contain Player-pool cards only. That artifact scope is separate from the access capability: changing
who may receive Game Master access does not implicitly publish Game Master card data.

Card-derived search, counts, ordering, validation, previews, notifications, and generated outputs apply their scope before exposing results. Direct restricted identities still use the established `404` policy, while an explicitly forbidden Game Master collection selection remains `403`.

## Capability-driven UI

The authenticated session payload exposes named capabilities such as developer-data and Game Master card access. Pages and navigation should consume these values instead of duplicating role checks in the frontend.

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
