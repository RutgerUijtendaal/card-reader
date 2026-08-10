import type { DeckRecord, DeckSummaryRecord } from '@/domain/decks/types';

export const isPlaytestDeckSummaryEligible = (deck: DeckSummaryRecord): boolean =>
  !deck.has_restricted_cards
  && (deck.status.deprecated_card_count ?? 0) === 0
  && deck.hero_card.restricted !== true
  && deck.hero_card.card_pool === 'player';

export const isPlaytestDeckEligible = (deck: DeckRecord): boolean => {
  if ((deck.status.deprecated_card_count ?? 0) > 0) return false;
  const cards = [
    deck.hero_card,
    ...deck.mainboard.entries.map((entry) => entry.card),
    ...deck.sideboards.flatMap((sideboard) => sideboard.entries.map((entry) => entry.card)),
  ];
  return cards.every((card) =>
    card.restricted !== true
    && card.card_pool === 'player'
    && card.lifecycle_status === 'active');
};
