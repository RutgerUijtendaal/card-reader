import type {
  PlaytestStorageAdapter,
} from '@/modules/playtester/types';
import { migrateStoredPlaytestDraft } from '@/modules/playtester/playtestState';

const STORAGE_PREFIX = 'card-reader.playtester.';

const storageKey = (deckId: string): string => `${STORAGE_PREFIX}${deckId}`;

export const createLocalPlaytestStorage = (): PlaytestStorageAdapter => ({
  load(deckId) {
    if (typeof localStorage === 'undefined') {
      return null;
    }
    const raw = localStorage.getItem(storageKey(deckId));
    if (!raw) {
      return null;
    }
    try {
      const parsed: unknown = JSON.parse(raw);
      return migrateStoredPlaytestDraft(parsed);
    } catch {
      return null;
    }
  },
  save(draft) {
    if (typeof localStorage === 'undefined') {
      return;
    }
    localStorage.setItem(storageKey(draft.deckId), JSON.stringify(draft));
  },
  clear(deckId) {
    if (typeof localStorage === 'undefined') {
      return;
    }
    localStorage.removeItem(storageKey(deckId));
  },
});
