import type { DeckRecord, DeckUpsertRequest } from '@/domain/decks/types';

export const buildDeckUpsertRequestFromRecord = (deck: DeckRecord): DeckUpsertRequest => ({
  name: deck.name.trim(),
  description_markup: deck.description_markup?.trim() || deck.description?.trim() || null,
  long_description_markup:
    deck.long_description_markup?.trim() || deck.long_description?.trim() || null,
  difficulty: deck.difficulty,
  visibility: deck.visibility,
  hero_card_id: deck.hero_card.id,
  tag_ids: (deck.tags ?? []).map((tag) => tag.id),
  suggested_type_labels: (deck.pending_tag_suggestions ?? []).map((suggestion) => suggestion.label),
  entries: deck.mainboard.entries.map((entry) => ({
    card_id: entry.card.id,
    quantity: entry.quantity,
  })),
  sideboards: deck.sideboards.map((sideboard) => ({
    id: sideboard.id,
    name: sideboard.name.trim(),
    entries: sideboard.entries.map((entry) => ({
      card_id: entry.card.id,
      quantity: entry.quantity,
    })),
  })),
});
