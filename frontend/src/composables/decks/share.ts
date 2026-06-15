import type { DeckVisibility } from '@/modules/decks/types';
import { buildPublicDeckLocation } from '@/composables/decks/deckRouteState';
import { router } from '@/router';

export const canShareDeck = (deck: { visibility: DeckVisibility }): boolean => deck.visibility !== 'private';

export const buildDeckSharePath = (deckId: string): string => router.resolve(buildPublicDeckLocation(deckId)).href;

export const buildDeckShareUrl = (deckId: string): string => {
  const sharePath = buildDeckSharePath(deckId);
  if (typeof window === 'undefined') {
    return sharePath;
  }
  return new URL(sharePath, window.location.origin).toString();
};
