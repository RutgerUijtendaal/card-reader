from card_reader_core.services.decks.normalization import DeckPayloadNormalizer


def test_normalize_markup_preserves_markdown_significant_whitespace() -> None:
    markup = "    [[card:id|Literal]]\r\nLine with a hard break  \r\n"

    assert DeckPayloadNormalizer().normalize_markup(markup) == (
        "    [[card:id|Literal]]\nLine with a hard break  \n"
    )


def test_normalize_markup_collapses_whitespace_only_values_to_none() -> None:
    assert DeckPayloadNormalizer().normalize_markup("  \r\n\t") is None
