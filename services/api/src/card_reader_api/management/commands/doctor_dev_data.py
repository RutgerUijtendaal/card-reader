from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.migrations.executor import MigrationExecutor
from django.db import connection

from card_reader_core.config.settings import settings
from card_reader_core.models import (
    HERO_CARD_ROLE,
    PLAYER_CARD_POOL,
    Card,
    CardBack,
    CardGroup,
    CardVersionImage,
    DeckTag,
    Keyword,
    Symbol,
    Tag,
    Template,
    Type,
    normalize_card_roles,
)
from card_reader_core.operations.developer_data.schema import DeveloperDataSelection
from card_reader_core.storage import build_storage_relative_path, resolve_storage_path


class Command(BaseCommand):
    help = "Verify that the local developer database is ready for the main application workflows."

    def handle(self, *args: object, **options: object) -> None:
        issues: list[str] = []
        executor = MigrationExecutor(connection)
        if executor.migration_plan(executor.loader.graph.leaf_nodes()):
            issues.append("database migrations are not current")
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
        selection_path = settings.developer_data_selection_path
        if selection_path.is_file():
            selection = DeveloperDataSelection.model_validate(
                json.loads(selection_path.read_text(encoding="utf-8"))
            )
            for template_key, required_roles in selection.coverage.required_template_role_hints.items():
                template = Template.objects.filter(key=template_key).first()
                if template is None:
                    issues.append(f"template {template_key} required for inference is missing")
                    continue
                missing = sorted(
                    set(required_roles) - set(normalize_card_roles(template.inferred_card_roles_json))
                )
                if missing:
                    issues.append(
                        f"template {template_key} is missing inference roles: {', '.join(missing)}"
                    )
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
        if not get_user_model().objects.filter(is_active=True, is_staff=True, is_superuser=True).exists():
            issues.append("an active local admin user is missing")
        card_back = CardBack.objects.filter(is_current=True).first()
        if card_back is None:
            issues.append("the current card back is missing")
        elif not resolve_storage_path(card_back.stored_path).is_file():
            issues.append("the current card-back asset is missing")
        missing_images = 0
        for stored_path in CardVersionImage.objects.values_list("stored_path", flat=True).iterator():
            if stored_path and not resolve_storage_path(stored_path).is_file():
                missing_images += 1
        if missing_images:
            issues.append(f"{missing_images} card-version image assets are missing")
        missing_symbol_assets = 0
        for reference_assets in Symbol.objects.values_list("reference_assets_json", flat=True).iterator():
            for stored_path in reference_assets:
                if stored_path:
                    symbol_asset_path = build_storage_relative_path("symbols", stored_path)
                    if not resolve_storage_path(symbol_asset_path).is_file():
                        missing_symbol_assets += 1
        if missing_symbol_assets:
            issues.append(f"{missing_symbol_assets} symbol reference assets are missing")
        if issues:
            raise CommandError("Developer-data readiness failed: " + "; ".join(issues))
        self.stdout.write(
            self.style.SUCCESS(
                f"Developer data is ready: {active_cards.count()} active cards, "
                f"storage={settings.storage_root_dir}."
            )
        )
