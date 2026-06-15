import type { DeckRecord } from '@/modules/decks/types';
import type { StoredPlaytestDraft } from '@/modules/playtester/types';

export type PlaytestRouteHandoff = {
  deck: DeckRecord;
  draft: StoredPlaytestDraft | null;
};

const routeHandoffs = new Map<string, PlaytestRouteHandoff>();

export const setPlaytestRouteHandoff = (
  deckId: string,
  handoff: PlaytestRouteHandoff,
): void => {
  routeHandoffs.set(deckId, handoff);
};

export const takePlaytestRouteHandoff = (deckId: string): PlaytestRouteHandoff | null => {
  const handoff = routeHandoffs.get(deckId) ?? null;
  routeHandoffs.delete(deckId);
  return handoff;
};

export const clearPlaytestRouteHandoffs = (): void => {
  routeHandoffs.clear();
};
