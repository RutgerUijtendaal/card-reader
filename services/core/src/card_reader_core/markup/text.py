from __future__ import annotations

import re
from collections.abc import Mapping
from collections.abc import Callable

from markdown_it import MarkdownIt


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
    return _transform_markup_text(markup, lambda value: value.replace(old_placeholder, new_placeholder))


def render_markup_plain(
    markup: str,
    *,
    symbol_tokens_by_key: Mapping[str, str] | None = None,
    compact: bool = False,
) -> str:
    symbols = symbol_tokens_by_key or {}
    protected_markup, reference_values = _protect_references(markup, symbols)
    parser = MarkdownIt("commonmark", {"html": False, "breaks": True})
    parser.disable("image")
    blocks: list[tuple[str, tuple[int, int] | None]] = []
    for token in parser.parse(protected_markup):
        if token.type == "inline":
            output: list[str] = []
            for child in token.children or []:
                if child.type == "text":
                    output.append(_restore_references(child.content, reference_values))
                elif child.type == "code_inline":
                    output.append(child.content)
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


def _protect_references(
    markup: str,
    symbol_tokens_by_key: Mapping[str, str],
) -> tuple[str, dict[str, str]]:
    output: list[str] = []
    values: dict[str, str] = {}
    position = 0
    fence_marker: tuple[str, int] | None = None
    inline_ticks = 0
    at_line_start = True
    while position < len(markup):
        if at_line_start and inline_ticks == 0:
            fence = re.match(r"( {0,3})(`{3,}|~{3,})([^\n]*)", markup[position:])
            if fence is not None:
                delimiter = fence.group(2)
                marker = delimiter[0]
                trailing_text = fence.group(3)
                opens_fence = fence_marker is None and not (
                    marker == "`" and "`" in trailing_text
                )
                closes_fence = (
                    fence_marker is not None
                    and marker == fence_marker[0]
                    and len(delimiter) >= fence_marker[1]
                    and not trailing_text.strip()
                )
                if opens_fence or closes_fence:
                    fence_marker = (marker, len(delimiter)) if opens_fence else None
                    prefix = f"{fence.group(1)}{delimiter}"
                    output.append(prefix)
                    position += len(prefix)
                    at_line_start = False
                    continue
        if fence_marker is None and markup[position] == "`":
            tick_match = re.match(r"`+", markup[position:])
            assert tick_match is not None
            tick_count = len(tick_match.group(0))
            if inline_ticks == 0:
                inline_ticks = tick_count
            elif tick_count == inline_ticks:
                inline_ticks = 0
            output.append(tick_match.group(0))
            position += tick_count
            at_line_start = False
            continue
        if fence_marker is None and inline_ticks == 0:
            card_match = CARD_REFERENCE_PATTERN.match(markup, position)
            symbol_match = SYMBOL_PLACEHOLDER_PATTERN.match(markup, position)
            match = card_match or symbol_match
            if match is not None:
                placeholder = f"CARDREADERREFERENCETOKEN{len(values)}X"
                if card_match is not None:
                    value = _ESCAPED_CARD_CHARACTER_PATTERN.sub(r"\1", card_match.group(2))
                else:
                    key = match.group(1)
                    token = symbol_tokens_by_key.get(key)
                    value = token if token is not None and token.strip() else key
                values[placeholder] = value
                output.append(placeholder)
                position = match.end()
                at_line_start = False
                continue
        character = markup[position]
        output.append(character)
        position += 1
        at_line_start = character == "\n"
    return "".join(output), values


def _restore_references(value: str, references: Mapping[str, str]) -> str:
    for placeholder, rendered in references.items():
        value = value.replace(placeholder, rendered)
    return value


def _transform_markup_text(markup: str, transform: Callable[[str], str]) -> str:
    # Markdown-it does not retain source offsets for inline children. Protect code ranges with
    # sentinels while applying this narrowly scoped token replacement.
    protected: dict[str, str] = {}

    def protect(match: re.Match[str]) -> str:
        key = f"\x00card-reader-code-{len(protected)}\x00"
        protected[key] = match.group(0)
        return key

    protected_markup = re.sub(
        r"(^|\n)(`{3,}|~{3,})[^\n]*\n.*?(?:\n\2[ \t]*(?=\n|$)|$)|(`+)(.*?)\3",
        protect,
        markup,
        flags=re.DOTALL,
    )
    transformed = transform(protected_markup)
    for key, original in protected.items():
        transformed = transformed.replace(key, original)
    return transformed
