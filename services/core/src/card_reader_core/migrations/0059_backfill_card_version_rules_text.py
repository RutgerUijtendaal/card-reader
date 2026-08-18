from collections.abc import Iterator, Mapping
import re
from typing import Any

from django.db import migrations
from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline

CARD_REFERENCE_PATTERN = re.compile(
    r"\[\[card:([^|\]\\\s]+)\|((?:\\.|[^\]\\])+)\]\]"
)
SYMBOL_PLACEHOLDER_PATTERN = re.compile(r"\[\[symbol:([a-z0-9-]+)\]\]")
ESCAPED_CARD_CHARACTER_PATTERN = re.compile(r"\\([\\|\]])")


BATCH_SIZE = 500


def _reference_rule(state: StateInline, silent: bool) -> bool:
    card_match = CARD_REFERENCE_PATTERN.match(state.src, state.pos)
    symbol_match = SYMBOL_PLACEHOLDER_PATTERN.match(state.src, state.pos)
    match = card_match or symbol_match
    if match is None:
        return False
    if not silent:
        if card_match is not None:
            token = state.push("card_reference", "", 0)
            token.meta = {
                "label": ESCAPED_CARD_CHARACTER_PATTERN.sub(r"\1", card_match.group(2))
            }
        else:
            token = state.push("symbol_reference", "", 0)
            token.meta = {"key": symbol_match.group(1) if symbol_match else ""}
    state.pos = match.end()
    return True


def _render_plain(markup: str, symbol_tokens_by_key: Mapping[str, str]) -> str:
    parser = MarkdownIt("commonmark", {"html": False, "breaks": True})
    parser.inline.ruler.before("text", "card_reader_reference", _reference_rule)
    parser.disable("image")
    blocks: list[tuple[str, tuple[int, int] | None]] = []
    for token in parser.parse(markup):
        if token.type == "inline":
            output: list[str] = []
            for child in token.children or []:
                if child.type in {"text", "code_inline"}:
                    output.append(child.content)
                elif child.type == "card_reference":
                    output.append(str(child.meta.get("label", "")))
                elif child.type == "symbol_reference":
                    key = str(child.meta.get("key", ""))
                    symbol_token = symbol_tokens_by_key.get(key)
                    output.append(
                        symbol_token
                        if symbol_token is not None and symbol_token.strip()
                        else key
                    )
                elif child.type in {"softbreak", "hardbreak"}:
                    output.append("\n")
            blocks.append(
                (
                    "".join(output),
                    (token.map[0], token.map[1]) if token.map is not None else None,
                )
            )
        elif token.type in {"code_block", "fence"}:
            blocks.append(
                (
                    token.content.rstrip("\n"),
                    (token.map[0], token.map[1]) if token.map is not None else None,
                )
            )

    output = []
    for index, (content, source_map) in enumerate(blocks):
        output.append(content)
        if index == len(blocks) - 1:
            continue
        next_map = blocks[index + 1][1]
        output.append(
            "\n\n"
            if source_map is not None
            and next_map is not None
            and next_map[0] > source_map[1]
            else "\n"
        )
    plain = "".join(output).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in plain.split("\n")]
    normalized: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        normalized.append(line)
        previous_blank = is_blank
    return "\n".join(normalized).strip()


def _batches(values: Iterator[Any]) -> Iterator[list[Any]]:
    batch: list[Any] = []
    for value in values:
        batch.append(value)
        if len(batch) == BATCH_SIZE:
            yield batch
            batch = []
    if batch:
        yield batch


def backfill_card_version_rules_text(apps: Any, schema_editor: Any) -> None:
    del schema_editor
    card_version_model = apps.get_model("card_reader_core", "CardVersion")
    version_symbol_model = apps.get_model("card_reader_core", "CardVersionSymbol")
    versions = card_version_model.objects.all().only(
        "id", "rules_text", "rules_text_enriched"
    )
    for batch in _batches(versions.iterator(chunk_size=BATCH_SIZE)):
        version_ids = [version.id for version in batch]
        symbols_by_version: dict[str, dict[str, str]] = {}
        symbol_rows = version_symbol_model.objects.filter(
            card_version_id__in=version_ids
        ).values_list("card_version_id", "symbol__key", "symbol__text_token")
        for version_id, symbol_key, text_token in symbol_rows:
            symbols_by_version.setdefault(str(version_id), {})[str(symbol_key)] = str(
                text_token
            )
        changed = []
        for version in batch:
            rendered = _render_plain(
                str(version.rules_text_enriched),
                symbols_by_version.get(str(version.id), {}),
            )
            if rendered == version.rules_text:
                continue
            version.rules_text = rendered
            changed.append(version)
        if changed:
            card_version_model.objects.bulk_update(
                changed,
                ["rules_text"],
                batch_size=BATCH_SIZE,
            )


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0058_deck_description_markup")]

    operations = [
        migrations.RunPython(
            backfill_card_version_rules_text,
            migrations.RunPython.noop,
        )
    ]
