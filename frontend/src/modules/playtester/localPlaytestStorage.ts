import type {
  PlaytestStorageAdapter,
  StoredPlaytestDraft,
} from '@/modules/playtester/types';
import { PLAYTEST_DRAFT_VERSION } from '@/modules/playtester/playtestState';

const STORAGE_PREFIX = 'card-reader.playtester.';

const isStoredDraft = (value: unknown): value is StoredPlaytestDraft => {
  if (value === null || typeof value !== 'object') {
    return false;
  }
  return 'version' in value
    && value.version === PLAYTEST_DRAFT_VERSION
    && 'deckId' in value
    && typeof value.deckId === 'string'
    && 'state' in value
    && value.state !== null
    && typeof value.state === 'object';
};

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
      return isStoredDraft(parsed) ? parsed : null;
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
