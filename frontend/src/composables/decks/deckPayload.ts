import type { DeckRecord, DeckUpsertRequest } from '@/modules/decks/types';

export const buildDeckUpsertRequestFromRecord = (deck: DeckRecord): DeckUpsertRequest => ({
  name: deck.name.trim(),
  description: deck.description?.trim() || null,
  visibility: deck.visibility,
  hero_card_id: deck.hero_card.id,
  entries: deck.mainboard.entries.map((entry) => ({
    card_id: entry.card.id,
    quantity: entry.quantity,
  })),
  sideboards: deck.sideboards.map((sideboard) => ({
    name: sideboard.name.trim(),
    entries: sideboard.entries.map((entry) => ({
      card_id: entry.card.id,
      quantity: entry.quantity,
    })),
  })),
});
