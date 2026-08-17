from card_reader_core.markup import (
    build_card_reference,
    render_markup_plain,
    replace_symbol_placeholder_key,
)


def test_render_markup_plain_preserves_structure_and_resolves_references() -> None:
    markup = """# Opening

Play **[[card:card-1|Bold Hero]]** with [[symbol:fire]].

- First
- Second
"""

    assert render_markup_plain(markup, symbol_tokens_by_key={"fire": "{F}"}) == (
        "Opening\n\nPlay Bold Hero with {F}.\n\nFirst\nSecond"
    )


def test_render_markup_plain_keeps_code_references_literal() -> None:
    markup = "Use `[[card:card-1|Hero]]` and:\n\n```text\n[[symbol:fire]]\n```"

    assert render_markup_plain(markup, symbol_tokens_by_key={"fire": "{F}"}) == (
        "Use [[card:card-1|Hero]] and:\n\n[[symbol:fire]]"
    )


def test_render_markup_plain_resumes_references_after_closing_fence() -> None:
    markup = "```\n[[card:inside|Inside]]\n```\n\n[[card:outside|Outside]]"

    assert render_markup_plain(markup) == "[[card:inside|Inside]]\n\nOutside"


def test_render_markup_plain_keeps_malformed_reference_literal_and_compacts_summary() -> None:
    markup = "**A**\n\n[[card:missing-label]]  B"

    assert render_markup_plain(markup, compact=True) == "A [[card:missing-label]] B"


def test_card_reference_builder_escapes_reserved_label_characters() -> None:
    reference = build_card_reference("card-1", "A | B] \\")

    assert reference == r"[[card:card-1|A \| B\] \\]]"
    assert render_markup_plain(reference) == "A | B] \\"


def test_symbol_key_refresh_ignores_inline_and_fenced_code() -> None:
    markup = "[[symbol:old]] `[[symbol:old]]`\n```\n[[symbol:old]]\n```"

    assert replace_symbol_placeholder_key(
        markup,
        old_symbol_key="old",
        new_symbol_key="new",
    ) == "[[symbol:new]] `[[symbol:old]]`\n```\n[[symbol:old]]\n```"
