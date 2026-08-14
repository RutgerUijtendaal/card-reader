from __future__ import annotations

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from card_reader_core.models import (
    Card,
    CardPool,
    CardPoolScope,
    CardVersion,
    Keyword,
    Symbol,
    Tag,
    Template,
    Type,
)
from card_reader_core.repositories.metadata import (
    replace_card_version_keywords,
    replace_card_version_tags,
    replace_card_version_types,
)
from card_reader_core.services.cards import get_filter_metadata


def _create_card_version(
    *,
    name: str,
    card_pool: CardPool,
    lifecycle_status: str = "active",
) -> tuple[Card, CardVersion]:
    card = Card.objects.create(
        key=f"{name.lower().replace(' ', '-')}-{uuid4().hex[:8]}",
        label=name,
        card_pool=card_pool,
        lifecycle_status=lifecycle_status,
    )
    version = CardVersion.objects.create(
        card=card,
        version_number=1,
        template=Template.objects.get(key="mtg-like-v1"),
        image_hash=f"hash-{uuid4().hex}",
        name=name,
    )
    return card, version


def _link_metadata(
    version: CardVersion,
    *,
    keyword: Keyword,
    tag: Tag,
    card_type: Type,
) -> None:
    replace_card_version_keywords(card_version_id=version.id, keyword_ids=[keyword.id])
    replace_card_version_tags(card_version_id=version.id, tag_ids=[tag.id])
    replace_card_version_types(card_version_id=version.id, type_ids=[card_type.id])


def _staff_client(username: str) -> Client:
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username=username,
        password="password",
        is_staff=True,
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    return client


def test_exact_pool_filter_metadata_uses_active_latest_card_links() -> None:
    shared_keyword = Keyword.objects.create(key="pool-shared-keyword", label="Pool Shared Keyword")
    shared_tag = Tag.objects.create(key="pool-shared-tag", label="Pool Shared Tag")
    shared_type = Type.objects.create(key="pool-shared-type", label="Pool Shared Type")
    pool_rows: dict[CardPool, tuple[Keyword, Tag, Type]] = {}

    for pool in ("player", "evil", "neutral"):
        keyword = Keyword.objects.create(key=f"{pool}-keyword", label=f"{pool.title()} Keyword")
        tag = Tag.objects.create(key=f"{pool}-tag", label=f"{pool.title()} Tag")
        card_type = Type.objects.create(key=f"{pool}-type", label=f"{pool.title()} Type")
        pool_rows[pool] = (keyword, tag, card_type)
        _card, version = _create_card_version(name=f"{pool.title()} Facet Card", card_pool=pool)
        replace_card_version_keywords(
            card_version_id=version.id,
            keyword_ids=[keyword.id, shared_keyword.id],
        )
        replace_card_version_tags(
            card_version_id=version.id,
            tag_ids=[tag.id, shared_tag.id],
        )
        replace_card_version_types(
            card_version_id=version.id,
            type_ids=[card_type.id, shared_type.id],
        )

    deprecated_keyword = Keyword.objects.create(
        key="deprecated-only-keyword",
        label="Deprecated Only Keyword",
    )
    deprecated_tag = Tag.objects.create(key="deprecated-only-tag", label="Deprecated Only Tag")
    deprecated_type = Type.objects.create(key="deprecated-only-type", label="Deprecated Only Type")
    _deprecated_card, deprecated_version = _create_card_version(
        name="Deprecated Facet Card",
        card_pool="player",
        lifecycle_status="deprecated",
    )
    _link_metadata(
        deprecated_version,
        keyword=deprecated_keyword,
        tag=deprecated_tag,
        card_type=deprecated_type,
    )

    historical_keyword = Keyword.objects.create(
        key="historical-only-keyword",
        label="Historical Only Keyword",
    )
    historical_tag = Tag.objects.create(key="historical-only-tag", label="Historical Only Tag")
    historical_type = Type.objects.create(key="historical-only-type", label="Historical Only Type")
    historical_card, historical_version = _create_card_version(
        name="Historical Facet Card",
        card_pool="player",
    )
    _link_metadata(
        historical_version,
        keyword=historical_keyword,
        tag=historical_tag,
        card_type=historical_type,
    )
    historical_version.is_latest = False
    historical_version.save(update_fields=["is_latest"])
    CardVersion.objects.create(
        card=historical_card,
        version_number=2,
        template=historical_version.template,
        image_hash=f"hash-{uuid4().hex}",
        name="Historical Facet Card",
        previous_version=historical_version,
    )

    for pool, (keyword, tag, card_type) in pool_rows.items():
        metadata = get_filter_metadata(
            card_pool_scope=CardPoolScope(frozenset({pool})),
            available_only=True,
        )
        keyword_keys = {row.key for row in metadata["keywords"]}
        tag_keys = {row.key for row in metadata["tags"]}
        type_keys = {row.key for row in metadata["types"]}

        assert keyword_keys == {keyword.key, shared_keyword.key}
        assert tag_keys == {tag.key, shared_tag.key}
        assert type_keys == {card_type.key, shared_type.key}


def test_omitted_scope_metadata_retains_complete_catalog_and_exact_scope_keeps_symbols() -> None:
    unlinked_keyword = Keyword.objects.create(key="unlinked-keyword", label="Unlinked Keyword")
    unlinked_tag = Tag.objects.create(key="unlinked-tag", label="Unlinked Tag")
    unlinked_type = Type.objects.create(key="unlinked-type", label="Unlinked Type")
    unlinked_symbol = Symbol.objects.create(
        key="unlinked-symbol",
        label="Unlinked Symbol",
        symbol_type="generic",
        detector_type="template",
        detection_config_json={},
        text_enrichment_json={},
        reference_assets_json=[],
        text_token="{UNLINKED}",
        enabled=True,
    )
    player_scope = CardPoolScope(frozenset({"player"}))

    global_metadata = get_filter_metadata(card_pool_scope=player_scope)
    exact_metadata = get_filter_metadata(card_pool_scope=player_scope, available_only=True)

    assert unlinked_keyword in global_metadata["keywords"]
    assert unlinked_tag in global_metadata["tags"]
    assert unlinked_type in global_metadata["types"]
    assert unlinked_keyword not in exact_metadata["keywords"]
    assert unlinked_tag not in exact_metadata["tags"]
    assert unlinked_type not in exact_metadata["types"]
    assert unlinked_symbol in global_metadata["symbols"]
    assert unlinked_symbol in exact_metadata["symbols"]


def test_exact_pool_filter_metadata_query_count_is_bounded() -> None:
    player_scope = CardPoolScope(frozenset({"player"}))
    with CaptureQueriesContext(connection) as empty_queries:
        get_filter_metadata(card_pool_scope=player_scope, available_only=True)

    for index in range(30):
        keyword = Keyword.objects.create(key=f"bounded-keyword-{index}", label=f"Keyword {index}")
        tag = Tag.objects.create(key=f"bounded-tag-{index}", label=f"Tag {index}")
        card_type = Type.objects.create(key=f"bounded-type-{index}", label=f"Type {index}")
        _card, version = _create_card_version(name=f"Bounded Query Card {index}", card_pool="player")
        _link_metadata(version, keyword=keyword, tag=tag, card_type=card_type)

    with CaptureQueriesContext(connection) as populated_queries:
        metadata = get_filter_metadata(card_pool_scope=player_scope, available_only=True)

    assert len(populated_queries) == len(empty_queries) == 4
    assert len(metadata["keywords"]) == 30
    assert len(metadata["tags"]) == 30
    assert len(metadata["types"]) == 30


def test_filter_metadata_api_validates_and_authorizes_explicit_pool_scope() -> None:
    keyword = Keyword.objects.create(key="evil-api-keyword", label="Evil API Keyword")
    tag = Tag.objects.create(key="evil-api-tag", label="Evil API Tag")
    card_type = Type.objects.create(key="evil-api-type", label="Evil API Type")
    _card, version = _create_card_version(name="Evil API Facet Card", card_pool="evil")
    _link_metadata(version, keyword=keyword, tag=tag, card_type=card_type)

    anonymous = Client(HTTP_HOST="localhost")
    assert anonymous.get("/cards/filters", {"card_pool": "evil"}).status_code == 403
    assert anonymous.get("/cards/filters", {"card_pool": "neutral"}).status_code == 403
    assert anonymous.get("/cards/filters", {"card_pool": "game_master"}).status_code == 400
    assert anonymous.get("/cards/filters", {"card_pool": "unknown"}).status_code == 400

    omitted_payload = anonymous.get("/cards/filters").json()
    assert keyword.key in {row["key"] for row in omitted_payload["keywords"]}

    staff = _staff_client("exact-filter-pool-staff")
    assert staff.get("/cards/filters", {"card_pool": "player"}).status_code == 200
    assert staff.get("/cards/filters", {"card_pool": "neutral"}).status_code == 200
    exact_payload = staff.get("/cards/filters", {"card_pool": "evil"}).json()
    assert {row["key"] for row in exact_payload["keywords"]} == {keyword.key}
    assert {row["key"] for row in exact_payload["tags"]} == {tag.key}
    assert {row["key"] for row in exact_payload["types"]} == {card_type.key}
