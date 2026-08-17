const DECK_EDITOR_PATH = /^\/my\/decks\/(?:new|[^/]+\/edit)$/;

export const resolveRouteViewKey = (
  path: string,
  workspaceGeneration: number,
): string | undefined => {
  if (DECK_EDITOR_PATH.test(path)) {
    return `deck-editor:${path}`;
  }
  if (path === '/notifications') {
    return `notifications:workspace-${workspaceGeneration}`;
  }
  return undefined;
};
