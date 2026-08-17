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
- [Tabletop Simulator imports](../tts/README.md) documents the shared persistent-sheet payload, native custom-deck creation, and stable artwork cache refresh.

## Planning

- [Campaign building plan](campaign-building-plan.md) preserves the proposed GM game-start flow, Campaign and pile domain boundaries, rule-resolution requirements, TTS direction, open decisions, and suggested delivery checkpoints.
