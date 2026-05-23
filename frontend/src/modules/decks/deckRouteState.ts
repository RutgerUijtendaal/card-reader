import type { LocationQuery, LocationQueryRaw, RouteLocationRaw } from 'vue-router';

const DECK_RETURN_TO = 'deck';
const DECK_RETURN_TO_QUERY_KEY = 'return_to';
const DECK_ID_QUERY_KEY = 'deck_id';

const queryString = (value: unknown): string | null =>
  typeof value === 'string' && value.trim().length > 0 ? value : null;

export const buildDeckCardDetailLocation = (
  cardId: string,
  deckId: string,
  query: LocationQuery,
): RouteLocationRaw => ({
  path: `/cards/${cardId}`,
  query: {
    ...query,
    [DECK_ID_QUERY_KEY]: deckId,
    [DECK_RETURN_TO_QUERY_KEY]: DECK_RETURN_TO,
  },
});

export const isDeckReturnQuery = (query: LocationQuery): boolean =>
  queryString(query[DECK_RETURN_TO_QUERY_KEY]) === DECK_RETURN_TO && queryString(query[DECK_ID_QUERY_KEY]) !== null;

export const buildDeckReturnLocation = (query: LocationQuery): RouteLocationRaw => {
  const deckId = queryString(query[DECK_ID_QUERY_KEY]);
  const nextQuery: LocationQueryRaw = { ...query };
  delete nextQuery[DECK_RETURN_TO_QUERY_KEY];
  delete nextQuery[DECK_ID_QUERY_KEY];
  return {
    path: deckId ? `/decks/${deckId}` : '/decks',
    query: nextQuery,
  };
};
