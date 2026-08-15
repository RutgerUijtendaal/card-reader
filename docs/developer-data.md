# Developer data

Developer-data bundles make a clean checkout usable without copying a production database or
storage directory. They are immutable, checksummed, sanitized onboarding snapshots hosted by the
website.

## Contents and exclusions

The reviewed `dev-data/selection.json` contains stable must-include keys, inclusion policy, and
coverage requirements. The current policy includes the complete Player card and Player card-group
catalog at build time; Evil and Neutral cards are excluded while those pools are restricted. The explicit
keys remain regression anchors that must still exist. The committed
`dev-data.lock.json` pins the required bundle version, format, checksum, and website API.

Selection, group validation, archive construction, and archive loading use a fixed canonical Player-only `CardPoolScope`. Selection keys resolve only against Player cards, so same-key Evil or Neutral twins neither override nor invalidate the selected Player card. Archive validation rejects non-Player card records and cross-pool groups even when an archive was produced outside the normal exporter. This publication scope is intentionally independent of the staff user who starts a build, so expanding interactive restricted-pool eligibility cannot expand published bundles accidentally.

Cards included through a selected group retain their exact database identity during selection; a
same-key Player card in another faction namespace is not pulled into the bundle merely because it
shares the group's member key.

Bundles contain complete catalogs, parsing-only templates, pool-specific classification rules, deck
tags, symbol assets, the current card back, and cards with the public relationships needed for
gallery, history, metadata, deck building, and Playtester workflows. Version 2 classification-rule
records identify their Tag or Type source by stable natural key; template records contain no role or
faction hints. Card records include the
required `card_pool`, canonical `card_roles`, and canonical `card_factions` fields; they never emit
the removed Hero boolean or internal faction identity key. Card-group anchors and members use a
structured card reference containing the pool, canonical faction set, and normalized card key, so
same-key cards in different faction namespaces remain distinct throughout validation and import.

The importer supports current Version 2 archives and explicitly adopts pinned Version 1 archives.
Version 1 adoption assigns every card to the Player pool and converts `is_hero=true` to the Hero role
before strict current-schema validation. It also supplies empty factions and an empty rule catalog.
Import reconstructs the
pool-plus-faction natural identity namespace rather than trusting a serialized internal key. This
compatibility keeps older immutable bundles usable without making current classification fields optional.

Selection coverage is evaluated by pool, role, and faction through `min_cards_by_pool`,
`min_cards_by_role`, and `min_cards_by_faction`. The existing Hero minimum is retained under the Hero
role. Evil and Neutral pool coverage remains zero while those pools are excluded; newly introduced
roles and Order, Blood, Dark, and Metal may remain at zero until reviewed source data is available. The
lock file is still generated only by publishing a validated immutable bundle and must not be edited by
hand.

`required_tag_keys` and `required_classification_rules` in the reviewed selection make expected
inference inputs explicit. Version 2 bundle validation and normal `doctor_dev_data` source-readiness
checks fail when a source Tag/Type or exact pool/target/source rule is missing.
`bootstrap_dev` passes the pinned source format to the doctor so the immutable Version 1 bundle is
checked only against fields it can represent. Templates and catalogs are supplied by developer-data
on a clean checkout; there is no parallel built-in catalog seed to keep in sync. The committed lock
continues to pin Version 1 so clean checkouts remain bootstrappable, but that bundle cannot contain
the new classification-rule catalog. After the compatible application is deployed, publish a Version
2 bundle through the normal staff workflow and commit its generated lock; never hand-edit the lock as
a substitute for that publish.

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

After the notification examples, bootstrap asks whether to generate the local TTS card sheets.
The default is **No** because rendering each full sheet can take a while. Choose **Yes** to render
them immediately with per-sheet progress, pass `--generate-tts-sheets` to opt in without a prompt,
or pass `--skip-tts-sheets` for a non-interactive fast bootstrap. Skipped sheets can be generated
later with:

```bash
uv run --project . --package card-reader-api python services/api/manage.py reconcile_tts_card_sheets --render
```

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
