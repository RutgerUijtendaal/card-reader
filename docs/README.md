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

The card-pool, role, and faction work is split into eleven dependency-ordered checkpoints. These documents describe intended work unless their status says they are implemented:

1. [Card classification Step 1: Foundation](card-classification-step-1-foundation.md) replaces the Hero flag with an initial Player/Game Master pool and multi-valued card roles, migrates existing data, preserves Hero behavior, adds editing/filtering, and establishes restricted-card access protection.
2. [Card classification Step 1.1: Authorization seam](card-classification-step-1-1-authorization-seam.md) consolidates user entitlement into an explicit core card-pool scope across queries, payloads, derived state, notifications, images, and published artifacts before the surface grows.
3. [Card classification Step 2: Import inference](card-classification-step-2-import-inference.md) adds explicit batch pools, automatic template/tag role inference, batch overrides, immutable job snapshots, and existing-card mismatch warnings.
4. [Card classification Step 2.1: Pool-scoped card identity](card-classification-step-2-1-pool-scoped-identity.md) replaces the temporary Game Master value with Evil and Neutral, makes normalized names, aliases, and import image matching unique within each of the three pools, and preserves id-based relationships and Player-only developer-data.
5. [Card classification Step 2.2: Import workflow seam](card-classification-step-2-2-import-workflow-seam.md) consolidates upload ownership and cleanup, transactional grouped reparses, frontend activity/detail refresh, and explicit evidence state before the workspace adds more callers.
6. [Card classification Step 2.3: Faction classification](card-classification-step-2-3-faction-classification.md) adds Order/Blood/Darkness as a second multi-valued facet, completes the role vocabulary, generalizes import classification mechanics, and scopes natural card identity by pool plus exact faction set.
7. [Card classification Step 3: Player, Evil, and Neutral workspaces](card-classification-step-3-card-pool-workspaces.md) adds the three-way sidenav context, single-pool route and collection scoping, workspace-aware navigation, and the final restricted-pool authorization audit.
8. [Card classification Step 3.1: Context-preserving workspace switching](card-classification-step-3-1-context-preserving-workspace-switching.md) keeps compatible global and resource routes mounted during workspace changes, centralizes route capability decisions, and limits Gallery fallback navigation to incompatible Player-only routes.
9. [Card classification Step 3.2: Admin-owned inference rules](card-classification-step-3-2-admin-owned-inference-rules.md) removes template hints and hard-coded tag policies, adds pool-specific Tag/Type inference rules to Admin Catalog, and snapshots those rules for deterministic imports.

### Post-classification hardening plans

1. [Card classification Step 4.0: Classification acceptance audit and cleanup](card-classification-step-4-filter-hardening.md) validates the completed classification feature as one system, fixes in-scope defects, and removes obsolete intermediate compatibility and duplication without adding new filter persistence.
2. [Card classification Step 4.1: Pool-aware Gallery filter surfaces](card-classification-step-4-1-pool-aware-gallery-filters.md) removes Roles from ordinary Gallery browsing, shows Factions only in Evil, shows Mana/Affinity/Devotion only in Player, and sanitizes hidden route and request state.

### Classification delivery model

- `feature/card-classification` is the umbrella integration branch. Its aggregate pull request targets `master` and remains open so CI and review can evaluate the complete feature as it grows.
- Each checkpoint is implemented on its own branch with a pull request targeting `feature/card-classification`, not `master`.
- Merge checkpoint pull requests into the umbrella branch in dependency order. Create the next checkpoint branch from the updated umbrella branch so its diff contains only that checkpoint.
- CI and automatic review must run on both checkpoint and aggregate pull requests. Do not retarget a checkpoint pull request merely to trigger them.
- Merge the umbrella pull request to `master` only after all eleven checkpoint acceptance criteria and the aggregate review are clear.
