---
name: card-reader-notifications
description: Work on Card Reader's in-app notification system. Use when adding notification types, changing notification storage/API/inbox behavior, wiring notification creation hooks from domain events, or planning future delivery channels such as email, push, realtime, or digest notifications.
---

# Card Reader Notifications

Follow `AGENTS.md` first. Use this skill with `card-reader-api` and `card-reader-frontend` when a change crosses backend notification behavior and the Vue notification surface.

## Core Rules

- Keep notifications core-owned. Store durable notification rows in `services/core`.
- Create notifications only through `NotificationService`; never write `UserNotification` rows directly from API views, frontend code, or feature call sites.
- Treat stored in-app notifications as the source of truth. Future email, push, realtime, and digest delivery must dispatch after notification creation.
- Keep channel-specific branching out of cards, decks, parse flags, and other domain services.
- Store rendered `title` and `message` snapshots for history, plus structured metadata for future UI or channel rendering.
- Every noisy event type must deliberately choose a stable `dedupe_key` or explicitly opt into one row per event.
- Treat staff parse-correction edits to the latest card version as silent; notify deck owners when card truth changes through a new card version becoming current, such as import-created replacement versions or explicit version promotion.

## Adding A Notification Type

1. Add a typed event helper or builder behind `NotificationService`.
2. Decide recipient, optional actor, event type, subject type/id, target URL, title, message, metadata, and dedupe key.
3. Hook the event at the domain write point after the write succeeds, preferably with `transaction.on_commit` for transactional workflows.
4. Skip notifying the actor when the actor is also the recipient unless product behavior explicitly says otherwise.
5. Add tests for creation, recipient isolation, read/unread count impact, and coalescing behavior.

## API And Frontend

- Keep notification API views transport-only: validate request data, enforce current-user ownership, and delegate to core repositories/services.
- Keep frontend notification API contracts in `frontend/src/modules/notifications`.
- Keep shared unread-count behavior in `frontend/src/composables/useNotificationSummary`.
- Keep the sidenav badge backed by `GET /notifications/summary`; do not duplicate unread-count state in page-only code.

## Future Delivery Channels

- Add delivery dispatchers after the in-app row is created.
- Base channel decisions on event type, recipient preferences, and metadata, not feature-specific conditionals in card/deck/flag code.
- Reuse stored notification snapshots when possible; render channel-specific copy only inside the dispatcher.
