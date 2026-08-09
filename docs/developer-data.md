# Developer data

Developer-data bundles make a clean checkout usable without copying a production database or
storage directory. They are immutable, checksummed, sanitized onboarding snapshots hosted by the
website.

## Contents and exclusions

The reviewed `dev-data/selection.json` contains stable must-include keys, inclusion policy, and
coverage requirements. The current policy includes the complete Player card and Player card-group
catalog at build time; Game Master cards are excluded while that pool is restricted. The explicit
keys remain regression anchors that must still exist. The committed
`dev-data.lock.json` pins the required bundle version, format, checksum, and website API.

Bundles contain complete catalogs, templates, deck tags, symbol assets, the current card back, and
cards with the public relationships needed for gallery, history, metadata, deck building, and
Playtester workflows. Version 2 card records include the required `card_pool` and canonical
`card_roles` fields; they never emit the removed Hero boolean.

The importer supports both current Version 2 archives and explicitly adopts pinned Version 1
archives. Version 1 adoption assigns every card to the Player pool and converts `is_hero=true` to
the Hero role before strict current-schema validation. This compatibility keeps older immutable
bundles usable without making Version 2 classification optional.

Selection coverage is evaluated by pool and by role through `min_cards_by_pool` and
`min_cards_by_role`. The existing Hero minimum is retained under the Hero role. Game Master pool
coverage remains zero while that pool is excluded; Boon and Event may remain at zero until reviewed
Player source data is available. The lock file is still
generated only by publishing a validated immutable bundle and must not be edited by hand.

They exclude accounts, decks, notifications, access and activity records, import jobs, uploads, raw
OCR, parse flags, suggestions, logs, debug crops, credentials, and source or server paths.

## Access

Active staff accounts always have developer-data access. Staff can grant or remove the Developer
role for regular accounts under **Admin → Users**. The role exposes developer-data metadata,
browser downloads, and bootstrap-code creation without granting broader staff permissions.

Role removal is checked during code exchange and every token-authorized download, so outstanding
bootstrap credentials stop working immediately. Bundle creation and build history remain
staff-only.

## Bootstrap a checkout

Sign in to the website, open **Settings → Developer Data**, generate a bootstrap code, then run:

```bash
pnpm bootstrap:dev
```

The command installs dependencies, migrates the empty local database, exchanges the code, downloads
the pinned bundle, verifies its checksum and manifest, imports records and media, prompts for local
admin credentials, creates development-only notification examples for that admin, and runs the
readiness doctor. The examples and their private demonstration deck are synthesized after import;
they are not part of the published developer-data bundle.

For an archive downloaded through the browser or provided offline:

```bash
pnpm bootstrap:dev --archive BUNDLE_ARCHIVE
```

To intentionally replace existing local data:

```bash
pnpm bootstrap:dev:reset
```

Reset is development-only and requires typing `RESET` after reviewing the resolved database and
storage targets. It creates a local safety archive under the gitignored
`.tmp/dev-data/reset-backups/` directory before replacing anything.

## Publish a version

Staff normally publish from **Settings → Developer Data**:

1. Choose **Build new version**.
2. Follow the durable build through queued, running, and completed states under **Operations**.
3. Download the generated `dev-data.lock.json` from the developer-data queue history.
4. Commit that lock file with the application change that should pin the bundle.

The dedicated builder worker exports the reviewed selection, validates it through an isolated
temporary import, and publishes it outside the HTTP process. Published versions are immutable and
retained for older branches. Production startup never imports developer data automatically.

The underlying management commands remain available for recovery and automation:

```bash
uv run --project . --package card-reader-api python services/api/manage.py export_dev_data \
  --selection dev-data/selection.json \
  --output .tmp/dev-data/BUNDLE_NAME.tar.gz

uv run --project . --package card-reader-api python services/api/manage.py run_dev_data_builder --once
```

Production uses Nginx internal redirects for authorized file transfer. Local development falls back
to Django `FileResponse`, so the same browser and bootstrap flows work without Nginx.

The Operations page also reports whether the dedicated builder process is online, idle, busy,
stopped, or stale. Build rows remain the durable source of truth if a worker heartbeat disappears.
