import { toAbsoluteApiUrl } from '@/shared/api/client';
import type { DeckCardSummary, DeckRecord } from '@/domain/decks/types';
import type { PlaytestCardInstance } from '@/features/playtester/types';

export type CardBackUrlsByCardId = Record<string, string>;

export const buildCardBackUrlsByCardId = (deck: DeckRecord | null): CardBackUrlsByCardId => {
  if (!deck) return {};
  const cards = [
    deck.hero_card,
    ...deck.mainboard.entries.map((entry) => entry.card),
    ...deck.sideboards.flatMap((sideboard) => sideboard.entries.map((entry) => entry.card)),
  ];
  return Object.fromEntries(
    cards.flatMap((card) => {
      const imageUrl = card.effective_card_back?.asset.image_url;
      return imageUrl ? [[card.id, toAbsoluteApiUrl(imageUrl)]] : [];
    }),
  );
};

export const resolvePlaytestCardBackUrl = (
  instance: PlaytestCardInstance,
  cardBackUrlsByCardId: CardBackUrlsByCardId,
  defaultCardBackUrl: string | null,
): string | null => {
  const currentUrl = cardBackUrlsByCardId[instance.cardId];
  if (currentUrl) return currentUrl;
  const storedUrl = (instance.card as Partial<DeckCardSummary>).effective_card_back?.asset.image_url;
  return storedUrl ? toAbsoluteApiUrl(storedUrl) : defaultCardBackUrl;
};
