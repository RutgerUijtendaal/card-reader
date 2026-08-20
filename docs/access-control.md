# Access Control

Card Reader combines public browsing with session-authenticated management tools. Backend capabilities are the source of truth; the frontend uses the session capability payload to decide which navigation and actions to show.

## Authentication and sessions

The web application uses Django session authentication. Login and session responses include a CSRF token, and unsafe browser requests require CSRF protection.

Inactive users cannot authenticate or continue using protected capabilities. The central authenticated-user predicate includes active status, so an existing session whose account becomes inactive is reported as unauthenticated and loses staff and other protected capabilities. Public card browsing remains available exactly as it is for any anonymous visitor. Sensitive token-based flows also re-check the issuing account instead of assuming that access remains valid for the token's entire lifetime.

## Access levels

The main access levels are:

- Public visitors can browse Player, Evil, and Neutral cards, groups, generations, and direct assets, plus public deck surfaces.
- Active authenticated users can use account-scoped features and other capabilities granted to ordinary members.
- Staff users can access administrative workflows including imports, review, catalogs, templates, exports, user management, and developer-data publishing.
- Admin and Review operate across all card pools; changing the shell workspace never narrows their catalogs, previews, counts, or queues. Imports require a fresh explicit card-pool selection and do not inherit the shell workspace.
- Superusers can access maintenance operations and the most sensitive administrative views.
- Developer users can download developer-data bundles even when they are not staff. Staff receive this capability automatically.

The developer flag is deliberately narrower than staff access: it supports project onboarding without granting import, catalog, user-management, or maintenance permissions. See [Developer data](developer-data.md) for its download and publishing flows.

## Public card pools

Player, Evil, and Neutral card data are public. Anonymous, ordinary, inactive-session, and staff viewers receive the same card visibility for collections, exact-pool filters, details, generations, groups, embedded payloads, and direct or immutable images. Invalid pool values are still rejected, lifecycle visibility is unchanged, and filesystem containment plus database ownership checks still protect immutable asset paths.

Staff permissions control actions and administrative workflows rather than card visibility. Imports, Review, Admin, catalog and template mutation, CSV export, and Gallery or content-version TTS creation remain staff-only. Their card-derived searches, counts, previews, and embedded data cover all pools once the endpoint-level permission succeeds.

Developer-data publication and the current deck workflow remain Player-only product contracts. Developer bundles intentionally publish Player content for onboarding. Deck creation, mutation, validation, Playtester eligibility, and deck TTS exports intentionally accept Player references only. Those boundaries do not conceal Evil or Neutral card identities: existing reclassified deck references are returned as real card payloads and marked through `has_non_player_cards`, while unsupported mutations remain invalid.

Persistent TTS sheets are partitioned by card pool and served through stable public sheet URLs for all three pools. Staff control Gallery and content-version export creation, while Tabletop Simulator can load the resulting sheets without a Django session and see later card-art updates at the same URL.

## Capability-driven UI

The authenticated session payload exposes named action capabilities but no card-pool entitlement list. The global sidenav always offers Player, Evil, and Neutral, including before login. Its saved workspace preference survives login, logout, and inactive-session transitions.

Workspace state is navigation context rather than authorization. Selection uses one typed route-capability policy: global routes stay mounted, Gallery replaces only its pool-owned state, resource routes retain the opened identity and update their return context, and Player-only routes fall back when the selected pool is incompatible. Route-changing selections commit after navigation is accepted, so a leave guard or superseding selection cannot partially change the stored context. Actively changing pools still invalidates pool-specific Gallery requests; session changes do not invalidate public card data or redirect public card and group routes.

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
- Keep credentials out of committed source.
