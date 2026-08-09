const DECK_EDITOR_PATH = /^\/my\/decks\/(?:new|[^/]+\/edit)$/;

export const resolveRouteViewKey = (path: string): string | undefined =>
  DECK_EDITOR_PATH.test(path) ? `deck-editor:${path}` : undefined;
