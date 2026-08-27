from __future__ import annotations

from argparse import ArgumentParser
import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.migrations.executor import MigrationExecutor
from django.db import connection
from django.db.models import QuerySet

from card_reader_core.config.settings import settings
from card_reader_core.models import (
    HERO_CARD_ROLE,
    PLAYER_CARD_POOL,
    Card,
    CardClassificationRule,
    CardGroup,
    CardVersionImage,
    DeckTag,
    Keyword,
    Symbol,
    Tag,
    Template,
    Type,
)
from card_reader_core.services.card_backs import get_pool_card_back_defaults
from card_reader_core.operations.developer_data.schema import (
    DEVELOPER_DATA_FORMAT_VERSION,
    SUPPORTED_DEVELOPER_DATA_FORMAT_VERSIONS,
    DeveloperDataSelection,
)
from card_reader_core.storage import build_storage_relative_path, resolve_storage_path


def _classification_rule_source_key(rule: CardClassificationRule) -> str:
    source = (
        rule.tag
        if rule.source_kind == "tag"
        else rule.type
        if rule.source_kind == "type"
        else rule.symbol
    )
    if source is None:
        return ""
    return source.key


class Command(BaseCommand):
    help = "Verify that the local developer database is ready for the main application workflows."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--source-format-version",
            type=int,
            choices=SUPPORTED_DEVELOPER_DATA_FORMAT_VERSIONS,
            default=DEVELOPER_DATA_FORMAT_VERSION,
            help=(
                "Validate only coverage representable by the imported bundle format. "
                "Defaults to the current format for source-data readiness checks."
            ),
        )

    def handle(self, *args: object, **options: object) -> None:
        issues: list[str] = []
        raw_source_format_version = options.get("source_format_version")
        if not isinstance(raw_source_format_version, int):
            raise CommandError("A valid source developer-data format version is required.")
        source_format_version = raw_source_format_version
        _append_database_issues(issues)
        _append_catalog_issues(issues)
        _append_selection_issues(issues, source_format_version=source_format_version)
        active_cards = _append_card_issues(issues)
        _append_admin_issue(issues)
        _append_asset_issues(issues)
        if issues:
            raise CommandError("Developer-data readiness failed: " + "; ".join(issues))
        self.stdout.write(
            self.style.SUCCESS(
                f"Developer data is ready: {active_cards.count()} active cards, "
                f"storage={settings.storage_root_dir}."
            )
        )


def _append_database_issues(issues: list[str]) -> None:
    executor = MigrationExecutor(connection)
    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
        issues.append("database migrations are not current")


def _append_catalog_issues(issues: list[str]) -> None:
    for label, model in (
        ("keywords", Keyword),
        ("tags", Tag),
        ("types", Type),
        ("symbols", Symbol),
        ("templates", Template),
        ("deck tags", DeckTag),
    ):
        if not model.objects.exists():
            issues.append(f"{label} are missing")


def _append_selection_issues(
    issues: list[str],
    *,
    source_format_version: int,
) -> None:
    selection_path = settings.developer_data_selection_path
    if not selection_path.is_file():
        return
    selection = DeveloperDataSelection.model_validate(
        json.loads(selection_path.read_text(encoding="utf-8"))
    )
    if source_format_version < 2:
        return
    missing_tags = sorted(
        set(selection.coverage.required_tag_keys) - set(Tag.objects.values_list("key", flat=True))
    )
    if missing_tags:
        issues.append(f"required inference tags are missing: {', '.join(missing_tags)}")
    _append_classification_rule_issues(
        issues,
        selection=selection,
        source_format_version=source_format_version,
    )


def _append_classification_rule_issues(
    issues: list[str],
    *,
    selection: DeveloperDataSelection,
    source_format_version: int,
) -> None:
    available_rules = {
        (
            rule.card_pool,
            rule.target_kind,
            rule.target_key,
            rule.source_kind,
            _classification_rule_source_key(rule),
            rule.enabled,
        )
        for rule in CardClassificationRule.objects.select_related("tag", "type", "symbol")
    }
    for rule in selection.coverage.required_classification_rules:
        if source_format_version == 2 and (
            rule.target_kind == "mana_family" or rule.source_kind == "symbol"
        ):
            continue
        identity = (
            rule.card_pool,
            rule.target_kind,
            rule.target_key,
            rule.source_kind,
            rule.source_key,
            rule.enabled,
        )
        if identity not in available_rules:
            issues.append(
                "required classification rule is missing: "
                f"{rule.card_pool}/{rule.target_kind}:{rule.target_key}"
                f"<-{rule.source_kind}:{rule.source_key}"
            )


def _append_card_issues(issues: list[str]) -> QuerySet[Card]:
    active_cards = Card.objects.filter(lifecycle_status="active")
    if not active_cards.filter(
        card_pool=PLAYER_CARD_POOL,
        role_assignments__role=HERO_CARD_ROLE,
    ).exists():
        issues.append("an active hero card is missing")
    mainboard_card_count = (
        active_cards.filter(card_pool=PLAYER_CARD_POOL)
        .exclude(role_assignments__role=HERO_CARD_ROLE)
        .distinct()
        .count()
    )
    if mainboard_card_count < 15:
        issues.append("at least 15 unique active mainboard cards are required")
    if not CardGroup.objects.exists():
        issues.append("representative card groups are missing")
    return active_cards


def _append_admin_issue(issues: list[str]) -> None:
    if (
        not get_user_model()
        .objects.filter(is_active=True, is_staff=True, is_superuser=True)
        .exists()
    ):
        issues.append("an active local admin user is missing")


def _append_asset_issues(issues: list[str]) -> None:
    card_back = get_pool_card_back_defaults()["player"]
    if card_back is None:
        issues.append("the current card back is missing")
    elif not resolve_storage_path(card_back.stored_path).is_file():
        issues.append("the current card-back asset is missing")
    missing_images = _missing_card_image_count()
    if missing_images:
        issues.append(f"{missing_images} card-version image assets are missing")
    missing_symbol_assets = _missing_symbol_asset_count()
    if missing_symbol_assets:
        issues.append(f"{missing_symbol_assets} symbol reference assets are missing")


def _missing_card_image_count() -> int:
    missing_images = 0
    for stored_path in CardVersionImage.objects.values_list("stored_path", flat=True).iterator():
        if stored_path and not resolve_storage_path(stored_path).is_file():
            missing_images += 1
    return missing_images


def _missing_symbol_asset_count() -> int:
    missing_symbol_assets = 0
    for reference_assets in Symbol.objects.values_list(
        "reference_assets_json", flat=True
    ).iterator():
        for stored_path in reference_assets:
            if stored_path:
                symbol_asset_path = build_storage_relative_path("symbols", stored_path)
                if not resolve_storage_path(symbol_asset_path).is_file():
                    missing_symbol_assets += 1
    return missing_symbol_assets
