import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import { buildGalleryLocation } from '@/composables/card-gallery/galleryNavigation';
import { buildAdminReturnLocation, isAdminReturnQuery } from '@/composables/admin/adminRouteState';
import { buildDeckReturnLocation, isDeckReturnQuery } from '@/composables/decks/deckRouteState';
import { addReturnToQuery, clearLocationQueryKeys, queryString } from '@/router/routeState';

const CARD_RETURN_TO = 'card';
const REVIEW_RETURN_TO = 'review';
const CARD_RETURN_TO_QUERY_KEY = 'return_to';
const CARD_ID_QUERY_KEY = 'card_id';
const REVIEW_VIEW_QUERY_KEY = 'review_view';
const REVIEW_STATUS_QUERY_KEY = 'review_status';

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

export const buildReviewCardEditorLocation = (
  cardId: string,
  query: LocationQuery,
  {
    versionId,
    propertyKey,
    view,
    status,
  }: {
    versionId: string;
    propertyKey: string;
    view: string;
    status: string;
  },
): RouteLocationRaw => ({
  path: `/cards/${cardId}/edit`,
  query: addReturnToQuery(query, REVIEW_RETURN_TO, {
    version_id: versionId,
    property_key: propertyKey,
    [REVIEW_VIEW_QUERY_KEY]: view,
    [REVIEW_STATUS_QUERY_KEY]: status,
  }),
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

const isReviewReturnQuery = (query: LocationQuery): boolean =>
  queryString(query[CARD_RETURN_TO_QUERY_KEY]) === REVIEW_RETURN_TO;

const buildReviewReturnLocation = (query: LocationQuery): RouteLocationRaw => ({
  path: '/review',
  query: {
    view: queryString(query[REVIEW_VIEW_QUERY_KEY]) ?? 'flags',
    status: queryString(query[REVIEW_STATUS_QUERY_KEY]) ?? 'open',
  },
});

export const buildCardReturnLocation = (query: LocationQuery): RouteLocationRaw => {
  if (isCardReturnQuery(query)) {
    return buildPreviousCardLocation(query);
  }
  if (isReviewReturnQuery(query)) {
    return buildReviewReturnLocation(query);
  }
  if (isAdminReturnQuery(query)) {
    return buildAdminReturnLocation(query);
  }
  if (isDeckReturnQuery(query)) {
    return buildDeckReturnLocation(query);
  }
  return buildGalleryLocation(query);
};

export const getCardReturnLabel = (query: LocationQuery): 'Gallery' | 'Admin' | 'Deck' | 'Card' | 'Review' => {
  if (isCardReturnQuery(query)) {
    return 'Card';
  }
  if (isReviewReturnQuery(query)) {
    return 'Review';
  }
  if (isAdminReturnQuery(query)) {
    return 'Admin';
  }
  if (isDeckReturnQuery(query)) {
    return 'Deck';
  }
  return 'Gallery';
};
