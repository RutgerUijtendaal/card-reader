import type { DeckRecord } from '@/domain/decks/types';

export type CardDeckReferenceSummary = DeckRecord & {
  card_reference: {
    as_hero: boolean;
    mainboard_quantity: number;
    sideboard_quantity: number;
  };
};
