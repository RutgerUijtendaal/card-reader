import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import { buildGalleryLocation } from '@/composables/card-gallery/galleryNavigation';
import { buildAdminReturnLocation, isAdminReturnQuery } from '@/composables/admin/adminRouteState';
import { buildDeckReturnLocation, isDeckReturnQuery } from '@/composables/decks/deckRouteState';
import { addReturnToQuery, clearLocationQueryKeys, queryString } from '@/router/routeState';

const CARD_RETURN_TO = 'card';
const CARD_RETURN_TO_QUERY_KEY = 'return_to';
const CARD_ID_QUERY_KEY = 'card_id';

export const isCardReturnQuery = (query: LocationQuery): boolean =>
  queryString(query[CARD_RETURN_TO_QUERY_KEY]) === CARD_RETURN_TO &&
  queryString(query[CARD_ID_QUERY_KEY]) !== null;

export const buildCardReturnQuery = (query: LocationQuery, cardId: string) =>
  addReturnToQuery(query, CARD_RETURN_TO, {
    [CARD_ID_QUERY_KEY]: cardId,
  });

export const buildCardEditorReturnLocation = (
  cardId: string,
  query: LocationQuery,
): RouteLocationRaw => ({
  path: `/cards/${cardId}/edit`,
  query: buildCardReturnQuery(query, cardId),
});

export const buildCardReturnContextLocation = (
  path: string,
  query: LocationQuery,
  cardId: string,
): RouteLocationRaw => ({
  path,
  query: buildCardReturnQuery(query, cardId),
});

const buildPreviousCardLocation = (query: LocationQuery): RouteLocationRaw => {
  const cardId = queryString(query[CARD_ID_QUERY_KEY]);
  return {
    path: cardId ? `/cards/${cardId}` : '/cards',
    query: clearLocationQueryKeys(query, [CARD_RETURN_TO_QUERY_KEY, CARD_ID_QUERY_KEY]),
  };
};

export const buildCardReturnLocation = (query: LocationQuery): RouteLocationRaw => {
  if (isCardReturnQuery(query)) {
    return buildPreviousCardLocation(query);
  }
  if (isAdminReturnQuery(query)) {
    return buildAdminReturnLocation(query);
  }
  if (isDeckReturnQuery(query)) {
    return buildDeckReturnLocation(query);
  }
  return buildGalleryLocation(query);
};

export const getCardReturnLabel = (query: LocationQuery): 'Gallery' | 'Admin' | 'Deck' | 'Card' => {
  if (isCardReturnQuery(query)) {
    return 'Card';
  }
  if (isAdminReturnQuery(query)) {
    return 'Admin';
  }
  if (isDeckReturnQuery(query)) {
    return 'Deck';
  }
  return 'Gallery';
};
