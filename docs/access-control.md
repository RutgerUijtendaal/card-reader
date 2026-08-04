# Access Control

Card Reader combines public browsing with session-authenticated management tools. Backend capabilities are the source of truth; the frontend uses the session capability payload to decide which navigation and actions to show.

## Authentication and sessions

The web application uses Django session authentication. Login and session responses include a CSRF token, and unsafe browser requests require CSRF protection.

Inactive users cannot authenticate or continue using protected capabilities. Sensitive token-based flows also re-check the issuing account instead of assuming that access remains valid for the token's entire lifetime.

## Access levels

The main access levels are:

- Public visitors can browse public card and deck surfaces and load public card and symbol assets.
- Active authenticated users can use account-scoped features and other capabilities granted to ordinary members.
- Staff users can access administrative workflows including imports, review, catalogs, templates, exports, user management, and developer-data publishing.
- Superusers can access maintenance operations and the most sensitive administrative views.
- Developer users can download developer-data bundles even when they are not staff. Staff receive this capability automatically.

The developer flag is deliberately narrower than staff access: it supports project onboarding without granting import, catalog, user-management, or maintenance permissions. See [Developer data](developer-data.md) for its download and publishing flows.

## Capability-driven UI

The authenticated session payload exposes named capabilities such as developer-data access. Pages and navigation should consume these values instead of duplicating role checks in the frontend.

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

