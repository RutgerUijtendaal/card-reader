import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import { buildGalleryLocation } from '@/modules/card-search/galleryNavigation';
import { addReturnToQuery, clearLocationQueryKeys, queryString } from '@/router/routeState';

const DECK_RETURN_TO = 'deck';
const DECKS_RETURN_TO = 'decks';
const GALLERY_RETURN_TO = 'gallery';
const MY_DECKS_RETURN_TO = 'my_decks';
const DECK_RETURN_TO_QUERY_KEY = 'return_to';
const DECK_ID_QUERY_KEY = 'deck_id';
const isGalleryContextPath = (path: string): boolean =>
  path === '/cards' || path.startsWith('/cards/') || path.startsWith('/card-groups/');

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

export const buildPublicDeckLocation = (deckId: string): RouteLocationRaw => ({
  path: `/decks/${deckId}`,
});

export const buildPublicDeckPath = (deckId: string): string => `/decks/${deckId}`;

export const isDeckReturnQuery = (query: LocationQuery): boolean =>
  queryString(query[DECK_RETURN_TO_QUERY_KEY]) === DECK_RETURN_TO && queryString(query[DECK_ID_QUERY_KEY]) !== null;

export const buildMyDecksLocation = (
  returnTo: typeof DECKS_RETURN_TO | typeof MY_DECKS_RETURN_TO = MY_DECKS_RETURN_TO,
): RouteLocationRaw => ({
  path: '/my/decks',
  query: returnTo === DECKS_RETURN_TO ? { return_to: DECKS_RETURN_TO } : {},
});

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

export const buildNewDeckEditorLocation = (
  returnTo: typeof MY_DECKS_RETURN_TO | typeof DECKS_RETURN_TO = MY_DECKS_RETURN_TO,
): RouteLocationRaw => ({
  path: '/my/decks/new',
  query: {
    return_to: returnTo,
  },
});

export const buildContextualNewDeckEditorLocation = (
  path: string,
  query: LocationQuery,
): RouteLocationRaw => {
  const explicitReturnTo = queryString(query[DECK_RETURN_TO_QUERY_KEY]);
  if (explicitReturnTo === DECKS_RETURN_TO) {
    return buildNewDeckEditorLocation(DECKS_RETURN_TO);
  }

  if (isGalleryContextPath(path)) {
    return {
      path: '/my/decks/new',
      query: addReturnToQuery(query, GALLERY_RETURN_TO),
    };
  }

  if (path === '/decks' || path.startsWith('/decks/')) {
    return buildNewDeckEditorLocation(DECKS_RETURN_TO);
  }

  return buildNewDeckEditorLocation(MY_DECKS_RETURN_TO);
};

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
  const clearedQuery = clearLocationQueryKeys(query, [DECK_RETURN_TO_QUERY_KEY, DECK_ID_QUERY_KEY]);

  if (returnTo === DECK_RETURN_TO && deckId) {
    return {
      path: `/my/decks/${deckId}`,
      query: clearedQuery,
    };
  }

  if (returnTo === DECKS_RETURN_TO) {
    return {
      path: '/decks',
      query: clearedQuery,
    };
  }

  if (returnTo === GALLERY_RETURN_TO) {
    return buildGalleryLocation(clearedQuery as LocationQuery);
  }

  return {
    path: '/my/decks',
    query: clearedQuery,
  };
};

export const getDeckEditorReturnLabel = (query: LocationQuery): 'Deck' | 'Decks' | 'Gallery' | 'My Decks' => {
  const returnTo = queryString(query[DECK_RETURN_TO_QUERY_KEY]);
  const deckId = queryString(query[DECK_ID_QUERY_KEY]);
  if (returnTo === DECK_RETURN_TO && deckId) {
    return 'Deck';
  }
  if (returnTo === DECKS_RETURN_TO) {
    return 'Decks';
  }
  if (returnTo === GALLERY_RETURN_TO) {
    return 'Gallery';
  }
  return 'My Decks';
};

export const buildMyDecksReturnLocation = (query: LocationQuery): RouteLocationRaw | null => {
  const returnTo = queryString(query[DECK_RETURN_TO_QUERY_KEY]);
  if (returnTo === DECKS_RETURN_TO) {
    return {
      path: '/decks',
      query: clearLocationQueryKeys(query, [DECK_RETURN_TO_QUERY_KEY, DECK_ID_QUERY_KEY]),
    };
  }
  return null;
};

export const getMyDecksReturnLabel = (query: LocationQuery): 'Decks' | '' => {
  const returnTo = queryString(query[DECK_RETURN_TO_QUERY_KEY]);
  return returnTo === DECKS_RETURN_TO ? 'Decks' : '';
};
