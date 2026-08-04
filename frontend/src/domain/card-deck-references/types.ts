import type { DeckRecord } from '@/domain/decks/types';

export type CardDeckReferenceSummary = DeckRecord & {
  card_reference: {
    is_hero: boolean;
    mainboard_quantity: number;
    sideboard_quantity: number;
  };
};
