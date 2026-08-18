from __future__ import annotations

import re
from collections.abc import Callable, Mapping

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline


SYMBOL_PLACEHOLDER_PATTERN = re.compile(r"\[\[symbol:([a-z0-9-]+)\]\]")
CARD_REFERENCE_PATTERN = re.compile(
    r"\[\[card:([^|\]\\\s]+)\|((?:\\.|[^\]\\])+)\]\]"
)
_ESCAPED_CARD_CHARACTER_PATTERN = re.compile(r"\\([\\|\]])")


def build_symbol_placeholder(symbol_key: str) -> str:
    return f"[[symbol:{symbol_key.strip().lower()}]]"


def build_card_reference(card_id: str, display_label: str) -> str:
    normalized_id = card_id.strip()
    if not normalized_id or any(character in normalized_id for character in "|]\\ \t\r\n"):
        raise ValueError("Card reference ids cannot contain whitespace or reserved characters.")
    escaped_label = (
        display_label.replace("\\", "\\\\").replace("|", "\\|").replace("]", "\\]")
    )
    return f"[[card:{normalized_id}|{escaped_label}]]"


def replace_symbol_placeholder_key(
    markup: str,
    *,
    old_symbol_key: str,
    new_symbol_key: str,
) -> str:
    old_placeholder = build_symbol_placeholder(old_symbol_key)
    new_placeholder = build_symbol_placeholder(new_symbol_key)
    return _transform_markup_text(
        markup,
        old_placeholder=old_placeholder,
        transform=lambda _value: new_placeholder,
    )


def render_markup_plain(
    markup: str,
    *,
    symbol_tokens_by_key: Mapping[str, str] | None = None,
    compact: bool = False,
) -> str:
    symbols = symbol_tokens_by_key or {}
    parser = _markup_parser()
    parser.disable("image")
    blocks: list[tuple[str, tuple[int, int] | None]] = []
    for token in parser.parse(markup):
        if token.type == "inline":
            output: list[str] = []
            for child in token.children or []:
                if child.type == "text":
                    output.append(child.content)
                elif child.type == "code_inline":
                    output.append(child.content)
                elif child.type == "card_reference":
                    output.append(str(child.meta.get("label", "")))
                elif child.type == "symbol_reference":
                    key = str(child.meta.get("key", ""))
                    symbol_token = symbols.get(key)
                    output.append(
                        symbol_token
                        if symbol_token is not None and symbol_token.strip()
                        else key
                    )
                elif child.type in {"softbreak", "hardbreak"}:
                    output.append("\n")
            source_map = (token.map[0], token.map[1]) if token.map is not None else None
            blocks.append(("".join(output), source_map))
            continue
        if token.type in {"code_block", "fence"}:
            source_map = (token.map[0], token.map[1]) if token.map is not None else None
            blocks.append((token.content.rstrip("\n"), source_map))

    output = []
    for index, (content, source_map) in enumerate(blocks):
        output.append(content)
        if index == len(blocks) - 1:
            continue
        next_map = blocks[index + 1][1]
        has_blank_source_line = (
            source_map is not None
            and next_map is not None
            and next_map[0] > source_map[1]
        )
        output.append("\n\n" if has_blank_source_line else "\n")
    plain = "".join(output)
    if compact:
        return " ".join(plain.split()).strip()
    lines = [line.rstrip() for line in plain.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    normalized: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        normalized.append(line)
        previous_blank = is_blank
    return "\n".join(normalized).strip()


def _markup_parser() -> MarkdownIt:
    parser = MarkdownIt(
        "commonmark",
        {"html": False, "breaks": True, "linkify": False, "typographer": False},
    )
    parser.inline.ruler.before("text", "card_reader_reference", _reference_rule)
    return parser


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
                "id": card_match.group(1),
                "label": _ESCAPED_CARD_CHARACTER_PATTERN.sub(r"\1", card_match.group(2)),
                "source_start": state.pos,
            }
        else:
            token = state.push("symbol_reference", "", 0)
            token.meta = {
                "key": symbol_match.group(1) if symbol_match else "",
                "source_start": state.pos,
            }
    state.pos = match.end()
    return True


def _transform_markup_text(
    markup: str,
    *,
    old_placeholder: str,
    transform: Callable[[str], str],
) -> str:
    output: list[str] = []
    cursor = 0
    while True:
        position = markup.find(old_placeholder, cursor)
        if position < 0:
            output.append(markup[cursor:])
            return "".join(output)
        output.append(markup[cursor:position])
        if _position_is_symbol_reference(markup, position, old_placeholder):
            output.append(transform(old_placeholder))
        else:
            output.append(old_placeholder)
        cursor = position + len(old_placeholder)


def _position_is_symbol_reference(
    markup: str,
    position: int,
    placeholder: str,
) -> bool:
    marker = _unused_marker(markup, "CARDREADERCARETPOSITION")
    marker_position = position
    while marker_position > 0 and markup[marker_position - 1] == "\\":
        marker_position -= 1
    marked_markup = (
        f"{markup[:marker_position]}{marker}{markup[marker_position:]}"
    )
    expected_key = SYMBOL_PLACEHOLDER_PATTERN.fullmatch(placeholder)
    if expected_key is None:
        return False
    for token in _markup_parser().parse(marked_markup):
        marker_offset = token.content.find(marker)
        if token.type != "inline" or marker_offset < 0:
            continue
        expected_start = (
            marker_offset + len(marker) + position - marker_position
        )
        children = token.children or []
        for child in children:
            if (
                child.type == "symbol_reference"
                and child.meta.get("key") == expected_key.group(1)
                and child.meta.get("source_start") == expected_start
            ):
                return True
    return False


def _unused_marker(value: str, base: str) -> str:
    marker = base
    while marker in value:
        marker += "X"
    return marker
