import { api } from '@/api/client';
import type { CardListItem, CardVersionDetail } from '@/modules/card-detail/types';

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

  const request = api
    .get<CardVersionDetail[]>(`/cards/${cardId}/generations`)
    .then(({ data }) => {
      const version = data.find((item) => item.is_latest) ?? data[0] ?? null;
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
