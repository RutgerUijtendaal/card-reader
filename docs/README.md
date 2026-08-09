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

The approved card-pool and multi-role work is split into three dependency-ordered plans. These documents describe intended work and should not be read as current shipped behavior:

1. [Card classification Step 1: Foundation](card-classification-step-1-foundation.md) replaces the Hero flag with a Player/Game Master pool and multi-valued card roles, migrates existing data, preserves Hero behavior, adds editing/filtering, and establishes Game Master access protection.
2. [Card classification Step 2: Import inference](card-classification-step-2-import-inference.md) adds explicit batch pools, automatic template/tag role inference, batch overrides, immutable job snapshots, and existing-card mismatch warnings.
3. [Card classification Step 3: Player and Game Master workspaces](card-classification-step-3-player-gm-workspaces.md) adds the staff-only Game Master sidenav context, route and collection scoping, workspace-aware navigation, and the final authorization audit.
