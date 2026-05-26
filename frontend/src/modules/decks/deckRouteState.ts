import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import { addReturnToQuery, clearLocationQueryKeys, queryString } from '@/router/routeState';

const DECK_RETURN_TO = 'deck';
const MY_DECKS_RETURN_TO = 'my_decks';
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

export const buildDeckEditorLocation = (
  deckId: string,
  query: LocationQuery,
): RouteLocationRaw => ({
  path: `/my/decks/${deckId}/edit`,
  query,
});

export const buildMyDeckEditorLocation = (deckId: string): RouteLocationRaw => ({
  path: `/my/decks/${deckId}/edit`,
  query: {
    return_to: MY_DECKS_RETURN_TO,
  },
});

export const buildNewDeckEditorLocation = (): RouteLocationRaw => ({
  path: '/my/decks/new',
  query: {
    return_to: MY_DECKS_RETURN_TO,
  },
});

export const buildDeckDetailEditorLocation = (deckId: string): RouteLocationRaw => ({
  path: `/my/decks/${deckId}/edit`,
  query: {
    return_to: DECK_RETURN_TO,
    deck_id: deckId,
  },
});

export const buildDeckEditorReturnLocation = (query: LocationQuery): RouteLocationRaw => {
  const returnTo = queryString(query[DECK_RETURN_TO_QUERY_KEY]);
  const deckId = queryString(query[DECK_ID_QUERY_KEY]);

  if (returnTo === DECK_RETURN_TO && deckId) {
    return {
      path: `/my/decks/${deckId}`,
      query: clearLocationQueryKeys(query, [DECK_RETURN_TO_QUERY_KEY, DECK_ID_QUERY_KEY]),
    };
  }

  return {
    path: '/my/decks',
    query: clearLocationQueryKeys(query, [DECK_RETURN_TO_QUERY_KEY, DECK_ID_QUERY_KEY]),
  };
};

export const getDeckEditorReturnLabel = (query: LocationQuery): 'Deck' | 'My Decks' => {
  const returnTo = queryString(query[DECK_RETURN_TO_QUERY_KEY]);
  const deckId = queryString(query[DECK_ID_QUERY_KEY]);
  return returnTo === DECK_RETURN_TO && deckId ? 'Deck' : 'My Decks';
};
