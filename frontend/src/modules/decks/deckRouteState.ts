import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import { addReturnToQuery, clearLocationQueryKeys, queryString } from '@/router/routeState';

const DECK_RETURN_TO = 'deck';
const DECK_RETURN_TO_QUERY_KEY = 'return_to';
const DECK_ID_QUERY_KEY = 'deck_id';

export const buildDeckCardDetailLocation = (
  cardId: string,
  deckId: string,
  query: LocationQuery,
): RouteLocationRaw => ({
  path: `/cards/${cardId}`,
  query: addReturnToQuery(query, DECK_RETURN_TO, {
    [DECK_ID_QUERY_KEY]: deckId,
  }),
});

export const isDeckReturnQuery = (query: LocationQuery): boolean =>
  queryString(query[DECK_RETURN_TO_QUERY_KEY]) === DECK_RETURN_TO && queryString(query[DECK_ID_QUERY_KEY]) !== null;

export const buildDeckReturnLocation = (query: LocationQuery): RouteLocationRaw => {
  const deckId = queryString(query[DECK_ID_QUERY_KEY]);
  return {
    path: deckId ? `/decks/${deckId}` : '/decks',
    query: clearLocationQueryKeys(query, [DECK_RETURN_TO_QUERY_KEY, DECK_ID_QUERY_KEY]),
  };
};
