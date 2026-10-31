"""Benchmark rendered loading endpoints against disposable, deterministic SQLite data.

Run with the API Python environment: python scripts/benchmark-loading.py --output .tmp/loading.json
No server, production data, or service test suite is used.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sqlite3
import statistics
import sys
import tempfile
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]


def stable_id(value: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"card-reader-benchmark/{value}"))


def seed(
    card_count: int,
    deck_count: int,
    storage: Path,
    snapshot_bytes: int,
    encounter_count: int = 0,
) -> object:
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from card_reader_core import models as m
    from card_reader_core.metadata import mana_family_sort_key_for_family_keys

    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    stamps = {"created_at": timestamp, "updated_at": timestamp}
    template = m.Template.objects.create(
        id=stable_id("template"),
        key="benchmark",
        label="Benchmark",
        definition_json={"regions": [{"configuration": "x" * 2048}]},
        **stamps,
    )
    content = m.ContentVersion.objects.create(
        id=stable_id("content"),
        version_number="99.0.0",
        base_version="99.0.0",
        major=99,
        minor=0,
        patch=0,
        description="Benchmark",
        **stamps,
    )
    owner = get_user_model().objects.create_user(
        username="benchmark", password=None, is_staff=True
    )
    image_path = storage / "images" / "benchmark.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"benchmark-image-placeholder")
    families = ("arcane", "dark", "divine", "martial", "occult", "primal")
    factions = ("order", "blood", "dark", "metal", "fire")
    cards, versions, images, roles, faction_rows, family_rows = [], [], [], [], [], []
    types, keywords, tags, symbols = [], [], [], []
    creature, _ = m.Type.objects.get_or_create(
        key="creature",
        defaults={"id": stable_id("creature"), "label": "Creature", **stamps},
    )
    mana, _ = m.Type.objects.get_or_create(
        key="mana", defaults={"id": stable_id("mana"), "label": "Mana", **stamps}
    )
    keyword, _ = m.Keyword.objects.get_or_create(
        key="arrival",
        defaults={"id": stable_id("arrival"), "label": "Arrival", **stamps},
    )
    tag, _ = m.Tag.objects.get_or_create(
        key="animal", defaults={"id": stable_id("animal"), "label": "Animal", **stamps}
    )
    symbol, _ = m.Symbol.objects.get_or_create(
        key="arcane-affinity",
        defaults={
            "id": stable_id("symbol"),
            "label": "Arcane",
            "symbol_type": "affinity",
            **stamps,
        },
    )
    for index in range(card_count):
        pool = (
            "player"
            if index < card_count * 0.7
            else ("evil" if index < card_count * 0.9 else "neutral")
        )
        family = families[index % len(families)]
        card = m.Card(
            id=stable_id(f"card-{index}"),
            key=f"benchmark-{index:05}",
            label=f"Card {index:05}",
            card_pool=pool,
            mana_family_sort_key=mana_family_sort_key_for_family_keys([family]),
            lifecycle_status="deprecated"
            if index > 100 and index % 29 == 0
            else "active",
            faction_identity_key=json.dumps([factions[index % 5]])
            if pool == "evil"
            else "[]",
            **stamps,
        )
        cards.append(card)
        family_rows.append(m.CardManaFamilyAssignment(card=card, mana_family=family))
        if pool == "evil":
            faction_rows.append(
                m.CardFactionAssignment(card=card, faction=factions[index % 5])
            )
        if index == 0 or index % 17 == 0:
            roles.append(
                m.CardRoleAssignment(
                    card=card, role="hero" if pool == "player" else "boss"
                )
            )
        previous = None
        for generation in (1, 2, 3):
            version = m.CardVersion(
                id=stable_id(f"version-{index}-{generation}"),
                card=card,
                template=template,
                version_number=generation,
                is_latest=generation == 3,
                previous_version=previous,
                content_version=content,
                image_hash=f"hash-{index}-{generation}",
                name=card.label,
                mana_value=index % 8,
                rules_text="Draw a card.",
                parsed_snapshot_json={"evidence": "x" * snapshot_bytes},
                field_sources_json={"name": "parser"},
                **stamps,
            )
            versions.append(version)
            previous = version
        card.latest_version = previous
        images.append(
            m.CardVersionImage(
                card_version=previous,
                stored_path="images/benchmark.png",
                source_file="images/benchmark.png",
                checksum=f"image-{index}",
                **stamps,
            )
        )
        types.append(
            m.CardVersionType(
                card_version=previous, type=mana if index % 5 == 0 else creature
            )
        )
        keywords.append(m.CardVersionKeyword(card_version=previous, keyword=keyword))
        tags.append(m.CardVersionTag(card_version=previous, tag=tag))
        symbols.append(m.CardVersionSymbol(card_version=previous, symbol=symbol))
    with transaction.atomic():
        # Insert the cyclic Card/latest-version relationship in two steps.
        for card in cards:
            card.latest_version_id = None
        m.Card.objects.bulk_create(cards)
        m.CardVersion.objects.bulk_create(versions)
        for index, card in enumerate(cards):
            card.latest_version_id = stable_id(f"version-{index}-3")
        m.Card.objects.bulk_update(cards, ["latest_version"])
        for model, rows in (
            (m.CardVersionImage, images),
            (m.CardRoleAssignment, roles),
            (m.CardFactionAssignment, faction_rows),
            (m.CardManaFamilyAssignment, family_rows),
            (m.CardVersionType, types),
            (m.CardVersionKeyword, keywords),
            (m.CardVersionTag, tags),
            (m.CardVersionSymbol, symbols),
        ):
            model.objects.bulk_create(rows)
        decks, entries, sideboards, side_entries = [], [], [], []
        # Shared staples plus rotating cards: overlap without identical decks.
        playable = [
            card
            for index, card in enumerate(cards[1:], 1)
            if card.card_pool == "player"
            and card.lifecycle_status == "active"
            and index % 17 != 0
        ]
        staples = playable[:16]
        rotating = playable[16:]
        for index in range(deck_count):
            selected = staples + [
                rotating[(index * 7 + offset) % len(rotating)] for offset in range(24)
            ]
            deck = m.Deck(
                id=stable_id(f"deck-{index}"),
                owner=owner,
                hero_card=cards[0],
                name=f"Deck {index:04}",
                visibility="public",
                **stamps,
            )
            decks.append(deck)
            entries.extend(
                m.DeckEntry(deck=deck, card=card, quantity=2, position=position)
                for position, card in enumerate(selected)
            )
            sideboard = m.DeckSideboard(
                id=stable_id(f"sideboard-{index}"), deck=deck, name="Options", **stamps
            )
            sideboards.append(sideboard)
            side_entries.extend(
                m.DeckSideboardEntry(
                    sideboard=sideboard, card=card, quantity=1, position=position
                )
                for position, card in enumerate(selected[-10:])
            )
        m.Deck.objects.bulk_create(decks)
        m.DeckEntry.objects.bulk_create(entries)
        m.DeckSideboard.objects.bulk_create(sideboards)
        m.DeckSideboardEntry.objects.bulk_create(side_entries)
        for index in range(100, card_count - 3, 20):
            if cards[index].lifecycle_status != "active":
                continue
            group = m.CardGroup.objects.create(
                id=stable_id(f"group-{index}"),
                key=f"group-{index}",
                name=f"Group {index}",
                anchor_card=cards[index],
                **stamps,
            )
            m.CardGroupMember.objects.bulk_create(
                [
                    m.CardGroupMember(
                        group=group, card=cards[index + offset], position=offset
                    )
                    for offset in range(3)
                ]
            )
        if encounter_count:
            seed_encounters(cards, owner, encounter_count, stamps)
    return owner


def seed_encounters(cards: list, owner: object, count: int, stamps: dict) -> None:
    from card_reader_core.models import CardGroup, CardGroupMember
    from card_reader_core.models.encounter import Encounter, EncounterEntry

    evil = [
        card
        for card in cards
        if card.card_pool == "evil" and card.lifecycle_status == "active"
    ]
    bosses = [
        card
        for index, card in enumerate(cards)
        if card.card_pool == "evil"
        and card.lifecycle_status == "active"
        and index % 17 == 0
    ]
    if not bosses:
        raise ValueError("Encounter fixture requires at least one active Evil boss")
    groups = []
    for index, boss in enumerate(bosses):
        group = CardGroup.objects.create(
            id=stable_id(f"encounter-group-{index}"),
            key=f"encounter-group-{index}",
            name=f"Boss group {index}",
            anchor_card=boss,
            **stamps,
        )
        members = [boss, *[card for card in evil[:4] if card.id != boss.id][:2]]
        CardGroupMember.objects.bulk_create(
            [
                CardGroupMember(group=group, card=card, position=position)
                for position, card in enumerate(members)
            ]
        )
        groups.append(group)
    records, entries = [], []
    for index in range(count):
        boss_index = index % len(bosses)
        record = Encounter(
            id=stable_id(f"encounter-{index}"),
            creator=owner,
            name="" if index % 11 == 10 else f"Encounter {index:04}",
            boss_card=bosses[boss_index],
            boss_group=groups[boss_index] if index % 2 == 0 else None,
            visibility="private" if index > 0 and index % 10 == 0 else "public",
            factions=["order"],
            **stamps,
        )
        records.append(record)
        selected = [
            evil[(index * 7 + offset) % len(evil)]
            for offset in range(min(40, len(evil)))
        ]
        entries.extend(
            EncounterEntry(
                id=stable_id(f"encounter-entry-{index}-{position}"),
                encounter=record,
                card=card,
                quantity=2,
                position=position,
            )
            for position, card in enumerate(selected)
        )
    Encounter.objects.bulk_create(records)
    EncounterEntry.objects.bulk_create(entries)


def benchmark(options: argparse.Namespace, storage: Path) -> dict[str, object]:
    os.environ.update(
        {
            "DJANGO_SETTINGS_MODULE": "card_reader_api.project.settings",
            "CARD_READER_DATABASE_PATH": str(storage / "benchmark.sqlite3"),
            "CARD_READER_APP_DATA_DIR": str(storage),
            "CARD_READER_ENVIRONMENT": "test",
        }
    )
    import django

    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection, connections
    from django.test.utils import CaptureQueriesContext
    from rest_framework.test import APIRequestFactory, force_authenticate
    from card_reader_api.cards.views import CardListView
    from card_reader_api.decks.views import (
        PublicDeckDetailView,
        PublicDeckListView,
        OwnerDeckListCreateView,
    )

    settings.DEBUG = False
    call_command("migrate", verbosity=0, interactive=False)
    owner = seed(
        options.cards,
        options.decks,
        storage,
        options.snapshot_bytes,
        options.encounters,
    )
    factory = APIRequestFactory()
    cases = []
    for pool in ("player", "evil", "neutral"):
        for grouped in (False, True):
            cases.append(
                (
                    f"gallery_{pool}_{'grouped' if grouped else 'cards'}",
                    CardListView,
                    {
                        "card_pool": pool,
                        "sort": "default",
                        "show_groups": str(grouped).lower(),
                        "page_size": 60,
                    },
                    {},
                    False,
                )
            )
    cases.extend(
        [
            (
                "gallery_filtered",
                CardListView,
                {
                    "card_pool": "player",
                    "q": "Card 00",
                    "sort": "default",
                    "page_size": 60,
                },
                {},
                False,
            ),
            (
                "gallery_grouped_page_5",
                CardListView,
                {
                    "card_pool": "player",
                    "sort": "default",
                    "show_groups": "true",
                    "page": 5,
                    "page_size": 60,
                },
                {},
                False,
            ),
            (
                "gallery_grouped_filtered",
                CardListView,
                {
                    "card_pool": "player",
                    "q": "Card 001",
                    "sort": "default",
                    "show_groups": "true",
                    "page_size": 60,
                },
                {},
                False,
            ),
            (
                "gallery_types",
                CardListView,
                {"card_pool": "player", "sort": "types_asc", "page_size": 60},
                {},
                False,
            ),
            (
                "deck_detail",
                PublicDeckDetailView,
                {},
                {"deck_id": stable_id("deck-0")},
                False,
            ),
            (
                "decks_public",
                PublicDeckListView,
                {
                    "view": "summary",
                    "page": 1,
                    "page_size": 24,
                    "snapshot_at": "2026-02-01T00:00:00Z",
                },
                {},
                False,
            ),
            (
                "decks_owner",
                OwnerDeckListCreateView,
                {
                    "view": "summary",
                    "page": 1,
                    "page_size": 24,
                    "snapshot_at": "2026-02-01T00:00:00Z",
                },
                {},
                True,
            ),
        ]
    )
    if options.encounters:
        from card_reader_api.encounters.views import (
            EncounterBossPickerView,
            PublicEncounterDetailView,
            PublicEncounterListView,
            StaffEncounterDetailView,
            StaffEncounterListView,
        )

        cases.extend(
            [
                (
                    "encounter_detail_group",
                    PublicEncounterDetailView,
                    {},
                    {"encounter_id": stable_id("encounter-0")},
                    False,
                ),
                (
                    "encounter_detail_single",
                    PublicEncounterDetailView,
                    {},
                    {"encounter_id": stable_id("encounter-1")},
                    False,
                ),
                (
                    "encounter_staff_detail",
                    StaffEncounterDetailView,
                    {},
                    {"encounter_id": stable_id("encounter-10")},
                    True,
                ),
                (
                    "encounters_public",
                    PublicEncounterListView,
                    {"page_size": 24},
                    {},
                    False,
                ),
                (
                    "encounters_staff",
                    StaffEncounterListView,
                    {"page_size": 24},
                    {},
                    True,
                ),
                (
                    "encounter_boss_picker",
                    EncounterBossPickerView,
                    {"page_size": 60, "sort": "default"},
                    {},
                    True,
                ),
            ]
        )
    if options.scenario_prefix:
        cases = [case for case in cases if case[0].startswith(options.scenario_prefix)]
    if not cases:
        raise ValueError("No benchmark scenarios selected")
    results = {}
    try:
        for name, view, params, kwargs, authenticated in cases:

            def request() -> bytes:
                req = factory.get("/benchmark", params)
                if authenticated:
                    force_authenticate(req, user=owner)
                response = view.as_view()(req, **kwargs)
                response.render()
                if response.status_code != 200:
                    raise RuntimeError(
                        f"{name}: {response.status_code}: {response.content!r}"
                    )
                return response.content

            request()  # Warm code paths and SQLite pages; no persistent response cache.
            durations = []
            for _ in range(options.repeats):
                start = perf_counter()
                payload = request()
                durations.append((perf_counter() - start) * 1000)
            with CaptureQueriesContext(connection) as captured:
                request()
            sql = [row["sql"] for row in captured.captured_queries]
            plans = []
            with connection.cursor() as cursor:
                for statement in sql[:2]:
                    if statement.lstrip().upper().startswith("SELECT"):
                        cursor.execute("EXPLAIN QUERY PLAN " + statement)
                        plans.append([list(row) for row in cursor.fetchall()])
            result = {
                "median_ms": round(statistics.median(durations), 2),
                "p95_ms": round(
                    sorted(durations)[math.ceil(len(durations) * 0.95) - 1], 2
                ),
                "queries": len(sql),
                "response_bytes": len(payload),
                "payload_sha256": hashlib.sha256(payload).hexdigest(),
                "samples_ms": [round(value, 2) for value in durations],
                "query_plans": plans,
                "sql": list(captured.captured_queries),
            }
            results[name] = result
            print(
                name,
                {
                    key: value
                    for key, value in result.items()
                    if key not in {"query_plans", "samples_ms", "payload_sha256", "sql"}
                },
                flush=True,
            )
        return {
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
            "django": django.get_version(),
            "platform": platform.platform(),
            "cards": options.cards,
            "versions_per_card": 3,
            "decks": options.decks,
            "encounters": options.encounters,
            "snapshot_bytes": options.snapshot_bytes,
            "repeats": options.repeats,
            "results": results,
        }
    finally:
        connections.close_all()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cards", type=int, default=3000)
    parser.add_argument("--decks", type=int, default=120)
    parser.add_argument("--encounters", type=int, default=0)
    parser.add_argument(
        "--scenario-prefix",
        default="",
        help="Only measure scenario names starting with this prefix",
    )
    parser.add_argument("--snapshot-bytes", type=int, default=4096)
    parser.add_argument("--repeats", type=int, default=15)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=ROOT,
        help="Checkout whose API/core code to measure",
    )
    parser.add_argument(
        "--compare",
        type=Path,
        help="Require response hashes to match this baseline report",
    )
    options = parser.parse_args()
    if 0 < options.encounters < 11:
        parser.error("encounters must be 0 or at least 11 for the detail scenarios")
    if (
        options.cards < 150
        or options.decks < 1
        or options.repeats < 1
        or options.snapshot_bytes < 0
        or options.encounters < 0
    ):
        parser.error("require cards >= 150, decks/repeats >= 1, snapshot-bytes >= 0")
    for service in ("core", "api"):
        sys.path.insert(
            0, str(options.source_root.resolve() / "services" / service / "src")
        )
    scratch = ROOT / ".tmp" / "codex" / "loading-benchmark"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as directory:
        report = benchmark(options, Path(directory))
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if options.compare:
        baseline = json.loads(options.compare.read_text(encoding="utf-8"))
        for key in ("cards", "decks", "snapshot_bytes", "versions_per_card"):
            if report[key] != baseline[key]:
                raise RuntimeError(f"Baseline fixture differs: {key}")
        if report["encounters"] != baseline.get("encounters", 0):
            raise RuntimeError("Baseline fixture differs: encounters")
        if report["results"].keys() != baseline["results"].keys():
            raise RuntimeError("Baseline scenarios differ")
        for name, result in report["results"].items():
            if result["payload_sha256"] != baseline["results"][name]["payload_sha256"]:
                raise RuntimeError(f"Response changed: {name}")
        print("All rendered response hashes match the baseline.")


if __name__ == "__main__":
    main()
