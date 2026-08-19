import { toAbsoluteApiUrl } from '@/shared/api/client';
import type { DeckCardSummary, DeckRecord } from '@/domain/decks/types';
import type { PlaytestCardInstance } from '@/features/playtester/types';

export type CardBackUrlsByCardId = Record<string, string | null>;

export const buildCardBackUrlsByCardId = (deck: DeckRecord | null): CardBackUrlsByCardId => {
  if (!deck) return {};
  const cards = [
    deck.hero_card,
    ...deck.mainboard.entries.map((entry) => entry.card),
    ...deck.sideboards.flatMap((sideboard) => sideboard.entries.map((entry) => entry.card)),
  ];
  return Object.fromEntries(cards.flatMap((card) => {
    if (!Object.prototype.hasOwnProperty.call(card, 'effective_card_back')) {
      return [];
    }
    const imageUrl = card.effective_card_back?.asset.image_url;
    return [[card.id, imageUrl ? toAbsoluteApiUrl(imageUrl) : null]];
  }));
};

export const resolvePlaytestCardBackUrl = (
  instance: PlaytestCardInstance,
  cardBackUrlsByCardId: CardBackUrlsByCardId,
  defaultCardBackUrl: string | null,
): string | null => {
  if (Object.prototype.hasOwnProperty.call(cardBackUrlsByCardId, instance.cardId)) {
    return cardBackUrlsByCardId[instance.cardId] ?? null;
  }
  const storedUrl = (instance.card as Partial<DeckCardSummary>).effective_card_back?.asset.image_url;
  return storedUrl ? toAbsoluteApiUrl(storedUrl) : defaultCardBackUrl;
};
