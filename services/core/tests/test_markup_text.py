import json
from pathlib import Path
from typing import TypedDict, cast

import pytest

from card_reader_core.markup import (
    build_card_reference,
    render_markup_plain,
    replace_symbol_placeholder_key,
)


class SharedMarkupCase(TypedDict):
    name: str
    markup: str
    plain: str
    compact_plain: str
    card_references: list[dict[str, str]]
    symbol_references: list[str]
    literal_text: list[str]


class SharedMarkupFixture(TypedDict):
    symbol_tokens: dict[str, str]
    cases: list[SharedMarkupCase]


SHARED_FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "test-fixtures" / "card-linked-markdown.json"
)
SHARED_FIXTURE = cast(
    SharedMarkupFixture,
    json.loads(SHARED_FIXTURE_PATH.read_text(encoding="utf-8")),
)


@pytest.mark.parametrize("fixture_case", SHARED_FIXTURE["cases"], ids=lambda case: case["name"])
def test_render_markup_plain_matches_shared_fixture(fixture_case: SharedMarkupCase) -> None:
    assert render_markup_plain(
        fixture_case["markup"],
        symbol_tokens_by_key=SHARED_FIXTURE["symbol_tokens"],
    ) == fixture_case["plain"]
    assert render_markup_plain(
        fixture_case["markup"],
        symbol_tokens_by_key=SHARED_FIXTURE["symbol_tokens"],
        compact=True,
    ) == fixture_case["compact_plain"]


def test_render_markup_plain_preserves_structure_and_resolves_references() -> None:
    markup = """# Opening

Play **[[card:card-1|Bold Hero]]** with [[symbol:fire]].

- First
- Second
"""

    assert render_markup_plain(markup, symbol_tokens_by_key={"fire": "{F}"}) == (
        "Opening\n\nPlay Bold Hero with {F}.\n\nFirst\nSecond"
    )


def test_render_markup_plain_resolves_references_after_unmatched_backticks() -> None:
    assert render_markup_plain("`note [[card:card-1|Hero]]") == "`note Hero"


def test_render_markup_plain_does_not_match_backticks_across_blocks() -> None:
    assert render_markup_plain("`note\n\n[[card:card-1|Hero]]`") == "`note\n\nHero`"


def test_render_markup_plain_keeps_escaped_references_literal() -> None:
    markup = r"\[[card:card-1|Hero]] \[[symbol:fire]]"

    assert render_markup_plain(markup, symbol_tokens_by_key={"fire": "{F}"}) == (
        "[[card:card-1|Hero]] [[symbol:fire]]"
    )


def test_render_markup_plain_resolves_card_labels_inside_markdown_links() -> None:
    assert render_markup_plain(
        "[see [[card:card-1|Card One]]](https://example.com)"
    ) == "see Card One"


def test_render_markup_plain_avoids_authored_placeholder_collisions() -> None:
    markup = "CARDREADERREFERENCETOKEN0X [[card:card-1|Hero]]"

    assert render_markup_plain(markup) == "CARDREADERREFERENCETOKEN0X Hero"


def test_render_markup_plain_keeps_code_references_literal() -> None:
    markup = "Use `[[card:card-1|Hero]]` and:\n\n```text\n[[symbol:fire]]\n```"

    assert render_markup_plain(markup, symbol_tokens_by_key={"fire": "{F}"}) == (
        "Use [[card:card-1|Hero]] and:\n\n[[symbol:fire]]"
    )


def test_render_markup_plain_keeps_indented_code_references_literal() -> None:
    markup = "    [[card:card-1|Hero]]\n\t[[symbol:fire]]"

    assert render_markup_plain(markup, symbol_tokens_by_key={"fire": "{F}"}) == (
        "[[card:card-1|Hero]]\n[[symbol:fire]]"
    )


def test_render_markup_plain_resumes_references_after_closing_fence() -> None:
    markup = "```\n[[card:inside|Inside]]\n```\n\n[[card:outside|Outside]]"

    assert render_markup_plain(markup) == "[[card:inside|Inside]]\n\nOutside"


def test_render_markup_plain_requires_a_valid_closing_fence() -> None:
    markup = (
        "````\n[[card:inside-1|Inside one]]\n```\n"
        "[[card:inside-2|Inside two]]\n```` not closed\n"
        "[[card:inside-3|Inside three]]\n````\n\n[[card:outside|Outside]]"
    )

    assert render_markup_plain(markup) == (
        "[[card:inside-1|Inside one]]\n```\n[[card:inside-2|Inside two]]\n"
        "```` not closed\n[[card:inside-3|Inside three]]\n\nOutside"
    )


def test_render_markup_plain_keeps_malformed_reference_literal_and_compacts_summary() -> None:
    markup = "**A**\n\n[[card:missing-label]]  B"

    assert render_markup_plain(markup, compact=True) == "A [[card:missing-label]] B"


def test_card_reference_builder_escapes_reserved_label_characters() -> None:
    reference = build_card_reference("card-1", "A | B] \\")

    assert reference == r"[[card:card-1|A \| B\] \\]]"
    assert render_markup_plain(reference) == "A | B] \\"


def test_symbol_key_refresh_ignores_inline_and_fenced_code() -> None:
    markup = (
        "[[symbol:old]] `[[symbol:old]]`\n```\n[[symbol:old]]\n```\n"
        "    [[symbol:old]]"
    )

    assert replace_symbol_placeholder_key(
        markup,
        old_symbol_key="old",
        new_symbol_key="new",
    ) == "[[symbol:new]] `[[symbol:old]]`\n```\n[[symbol:old]]\n```\n    [[symbol:old]]"


def test_symbol_key_refresh_ignores_escaped_placeholders() -> None:
    assert replace_symbol_placeholder_key(
        r"\[[symbol:old]] [[symbol:old]]",
        old_symbol_key="old",
        new_symbol_key="new",
    ) == r"\[[symbol:old]] [[symbol:new]]"
