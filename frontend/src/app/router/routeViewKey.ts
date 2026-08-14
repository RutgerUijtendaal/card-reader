const DECK_EDITOR_PATH = /^\/my\/decks\/(?:new|[^/]+\/edit)$/;

export const resolveRouteViewKey = (path: string): string | undefined =>
  DECK_EDITOR_PATH.test(path) ? `deck-editor:${path}` : undefined;

export const resolveWorkspaceAwareRouteViewKey = (
  path: string,
  workspaceGeneration: number,
  isCardPoolWorkspace: boolean,
): string | undefined => {
  const routeKey = resolveRouteViewKey(path);
  if (!isCardPoolWorkspace) {
    return routeKey;
  }
  return `${routeKey ?? path}:workspace:${workspaceGeneration}`;
};
