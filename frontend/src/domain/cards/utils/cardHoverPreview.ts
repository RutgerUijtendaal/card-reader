import { fetchCardVersions } from '@/domain/cards/api';
import type { CardListItem, CardVersionDetail } from '@/domain/cards/types';

const hoverCardCache = new Map<string, CardListItem>();
const inFlightHoverCardRequests = new Map<string, Promise<CardListItem | null>>();

const toCardListItem = (version: CardVersionDetail): CardListItem => ({
  ...version,
  result_type: 'card',
});

export const fetchHoverPreviewCard = async (cardId: string): Promise<CardListItem | null> => {
  const cached = hoverCardCache.get(cardId);
  if (cached) {
    return cached;
  }

  const inFlight = inFlightHoverCardRequests.get(cardId);
  if (inFlight) {
    return inFlight;
  }

  const request = fetchCardVersions(cardId)
    .then((versions) => {
      const version = versions.find((item) => item.is_latest) ?? versions[0] ?? null;
      if (!version) {
        return null;
      }
      const card = toCardListItem(version);
      hoverCardCache.set(cardId, card);
      return card;
    })
    .catch(() => null)
    .finally(() => {
      inFlightHoverCardRequests.delete(cardId);
    });

  inFlightHoverCardRequests.set(cardId, request);
  return request;
};

export const clearHoverPreviewCardCache = (): void => {
  hoverCardCache.clear();
  inFlightHoverCardRequests.clear();
};
