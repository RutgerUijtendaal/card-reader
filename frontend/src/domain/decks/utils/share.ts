import type { DeckVisibility } from '@/domain/decks/types';
import { buildPublicDeckPath } from '@/domain/decks/utils/deckRouteState';

export const canShareDeck = (deck: { visibility: DeckVisibility }): boolean => deck.visibility !== 'private';

export const buildDeckSharePath = (deckId: string): string => buildPublicDeckPath(deckId);

export const buildDeckShareUrl = (deckId: string): string => {
  const sharePath = buildDeckSharePath(deckId);
  if (typeof window === 'undefined') {
    return sharePath;
  }
  return new URL(sharePath, window.location.origin).toString();
};
