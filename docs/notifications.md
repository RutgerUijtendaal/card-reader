# Notifications

Card Reader currently delivers notifications through one durable channel: the authenticated in-app inbox. `UserNotification` rows are the source of truth for inbox history and the unread badge.

The inbox is one chronological feed. New rows retain an unread indicator until opened, event-type filters are applied server-side, and older results append through the shared load-more pattern.

## Event catalog

### `parse_flag_item.reviewed`

- Recipient: the user who submitted the parse flag.
- Actor: the staff reviewer. Reviewers do not notify themselves in production; development and test environments retain self-review notifications so the inbox presentation can be exercised with one account.
- Trigger: an individual flag item is resolved or dismissed.
- Subject: the reviewed flag item.
- Target: the exact reviewed card version.
- Metadata: card and version identity, field label, submitted suggestion or note, review result, reviewer snapshot, and reviewer response.
- Coalescing: repeated reviews of the same item share one unread row.

### `deck.card_version_changed`

- Recipient: every owner of a deck that references the card as its hero, in the mainboard, or in a sideboard. Actors do not notify themselves.
- Trigger: a newly imported card version becomes current, or a different existing version is explicitly promoted to current.
- Subject: the affected deck and card pair.
- Targets: the affected deck and the card detail page.
- Metadata: deck, card, the before and after card versions, and the typed import or promotion cause. The inbox loads those exact versions on demand for an interactive image comparison whose divider reveals each printing in place.
- Coalescing: repeated current-version changes for the same unread deck/card pair increment the existing row.

Ordinary edits to the current version, reparses that reuse the existing version, and no-op promotions are intentionally silent.

## Development examples

Local API startup and `pnpm bootstrap:dev` idempotently seed representative notifications for active
staff users. The examples include an expanded flag-review response and a card-version change backed
by two real image-bearing printings. A private `Notification Layout Examples` deck is created so the
deck and card actions remain valid. These rows are synthesized locally through `NotificationService`;
notifications and decks remain excluded from published developer-data bundles.

To refresh missing examples without restarting the API, run:

```bash
uv run --project . --package card-reader-api python services/api/manage.py seed_notification_examples
```

## Ownership and delivery

Feature services call typed helpers on `NotificationService` only after their domain write succeeds. `NotificationService` owns recipients, copy, metadata, targets, and deduplication keys; repositories own persistence and unread coalescing. API views only serialize and update the current user's rows. The Vue inbox maps known event metadata into event-specific timeline entries and falls back to stored title and message snapshots for incomplete historical or unknown events.

Future email, push, realtime, or digest delivery should dispatch after the in-app row is created and use the stored event type, snapshots, and metadata instead of adding channel logic to card, deck, or flag services.
