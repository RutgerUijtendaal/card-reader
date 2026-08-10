# Card Reader Documentation

This directory contains feature descriptions, operational guides, and technical references for Card Reader. The root README stays focused on installing and running the project; deeper explanations live here.

## Feature guides

- [Imports and parsing](imports-and-parsing.md) explains how uploaded card images move through the asynchronous parser and into reviewable card records.
- [Card management](card-management.md) describes card identities, versions, metadata, lifecycle state, groups, aliases, and merges.
- [Deck building](deck-building.md) covers deck structure, visibility, validation, and configurable deck-building constraints.
- [Playtester](playtester.md) explains the local manual playtest sandbox, opening flow, zones, interactions, and draft persistence.
- [Access control](access-control.md) describes public, authenticated, staff, superuser, and developer access, including managed users and access requests.
- [Notifications](notifications.md) describes durable in-app notifications and how domain events produce them.

## Operations and onboarding

- [Developer data](developer-data.md) covers authenticated development bundles, clean-checkout bootstrapping, publishing, and local behavior.
- [Backup and restore](backups.md) covers recovery archives, restore behavior, retention, and operational safeguards.

## Reference

- [Card database diagram](card-database-diagram.svg) shows the main card, version, metadata, import, group, and deck relationships.
- [Tabletop Simulator imports](../tts/README.md) documents name-matched deck cloning, direct custom-card exports, and stable artwork cache refresh.

## Implementation plans

The approved card-pool and multi-role work is split into four dependency-ordered checkpoints. These documents describe intended work unless their status says they are implemented:

1. [Card classification Step 1: Foundation](card-classification-step-1-foundation.md) replaces the Hero flag with a Player/Game Master pool and multi-valued card roles, migrates existing data, preserves Hero behavior, adds editing/filtering, and establishes Game Master access protection.
2. [Card classification Step 1.1: Authorization seam](card-classification-step-1-1-authorization-seam.md) consolidates user entitlement into an explicit core card-pool scope across queries, payloads, derived state, notifications, images, and published artifacts before the surface grows.
3. [Card classification Step 2: Import inference](card-classification-step-2-import-inference.md) adds explicit batch pools, automatic template/tag role inference, batch overrides, immutable job snapshots, and existing-card mismatch warnings.
4. [Card classification Step 3: Player and Game Master workspaces](card-classification-step-3-player-gm-workspaces.md) adds the staff-only Game Master sidenav context, route and collection scoping, workspace-aware navigation, and the final authorization audit.

### Classification delivery model

- `feature/card-classification` is the umbrella integration branch. Its aggregate pull request targets `master` and remains open so CI and review can evaluate the complete feature as it grows.
- Each checkpoint is implemented on its own branch with a pull request targeting `feature/card-classification`, not `master`.
- Merge checkpoint pull requests into the umbrella branch in dependency order. Create the next checkpoint branch from the updated umbrella branch so its diff contains only that checkpoint.
- CI and automatic review must run on both checkpoint and aggregate pull requests. Do not retarget a checkpoint pull request merely to trigger them.
- Merge the umbrella pull request to `master` only after all four checkpoint acceptance criteria pass and the aggregate review is clear.
