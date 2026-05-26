import type { DeckRecord } from '@/modules/decks/types';
import { buildPublicDeckPath } from '@/modules/decks/deckRouteState';

export const canShareDeck = (deck: DeckRecord): boolean => deck.visibility !== 'private';

export const buildDeckSharePath = (deckId: string): string => buildPublicDeckPath(deckId);

export const buildDeckShareUrl = (deckId: string): string => {
  const sharePath = buildDeckSharePath(deckId);
  if (typeof window === 'undefined') {
    return sharePath;
  }
  return new URL(sharePath, window.location.origin).toString();
};
