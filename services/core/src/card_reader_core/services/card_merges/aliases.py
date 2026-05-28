from __future__ import annotations

from card_reader_core.models import Card, CardAlias, CardVersion
from card_reader_core.repositories.helpers import normalize_slug_key

from .types import CardMergeAliasPreview, CardMergeError


def resolve_card_by_name_key(name: str) -> Card | None:
    key = normalize_slug_key(name)
    if not key:
        return None
    card = Card.objects.filter(key=key).first()
    if card is not None:
        return card
    alias = CardAlias.objects.select_related("card").filter(key=key).first()
    return alias.card if alias is not None else None


def ensure_card_alias(
    *,
    card: Card,
    key: str,
    label: str,
    allowed_conflict_card_ids: set[str] | None = None,
) -> CardAlias | None:
    normalized_key = normalize_slug_key(key)
    if not normalized_key or normalized_key == card.key:
        return None
    allowed_conflicts = allowed_conflict_card_ids or set()
    existing_card = Card.objects.filter(key=normalized_key).exclude(id=card.id).first()
    if existing_card is not None and existing_card.id not in allowed_conflicts:
        raise CardMergeError(f"Alias key '{normalized_key}' is already used by card '{existing_card.id}'.")
    existing_alias = CardAlias.objects.filter(key=normalized_key).first()
    if existing_alias is not None:
        existing_alias_card_id = str(getattr(existing_alias, "card_id"))
        if existing_alias_card_id != card.id:
            raise CardMergeError(f"Alias key '{normalized_key}' already points to card '{existing_alias_card_id}'.")
        return existing_alias
    return CardAlias.objects.create(card=card, key=normalized_key, label=label)


def build_alias_previews(*, target: Card, sources: list[Card]) -> list[CardMergeAliasPreview]:
    candidates: dict[str, str] = {}
    source_ids = [source.id for source in sources]
    for source in sources:
        if source.key:
            candidates[source.key] = source.label or source.key
    for alias in CardAlias.objects.filter(card_id__in=source_ids).order_by("key"):
        candidates[alias.key] = alias.label or alias.key
    for version in CardVersion.objects.filter(card_id__in=source_ids).order_by("created_at", "version_number", "id"):
        key = normalize_slug_key(version.name)
        if key:
            candidates.setdefault(key, version.name)

    aliases: list[CardMergeAliasPreview] = []
    for key, label in sorted(candidates.items()):
        if key == target.key:
            continue
        existing_alias = CardAlias.objects.filter(key=key).first()
        existing_alias_card_id = str(getattr(existing_alias, "card_id")) if existing_alias is not None else None
        conflict_card_id = existing_alias_card_id if existing_alias_card_id is not None and existing_alias_card_id != target.id else None
        card_conflict = Card.objects.filter(key=key).exclude(id__in=[target.id, *source_ids]).first()
        if card_conflict is not None:
            conflict_card_id = card_conflict.id
        aliases.append(CardMergeAliasPreview(key=key, label=label, conflict_card_id=conflict_card_id))
    return aliases
