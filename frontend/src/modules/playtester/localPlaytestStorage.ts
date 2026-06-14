import type {
  PlaytestOpeningSetup,
  PlaytestPhase,
  PlaytestState,
  PlaytestStorageAdapter,
  StoredPlaytestDraft,
} from '@/modules/playtester/types';
import {
  EMPTY_OPENING_SETUP,
  PLAYTEST_DRAFT_VERSION,
  ensurePlaytestInstanceShape,
  normalizePileGroups,
} from '@/modules/playtester/playtestState';

const STORAGE_PREFIX = 'card-reader.playtester.';

type LegacyStoredPlaytestDraft = Omit<StoredPlaytestDraft, 'version'> & {
  version: 1 | 2;
};

type MigratableStoredDraft = Omit<StoredPlaytestDraft, 'version' | 'state'> & {
  version: number;
  state: Omit<PlaytestState, 'phase' | 'openingSetup'> & {
    openingSetup?: PlaytestOpeningSetup;
    phase: PlaytestPhase | 'setup';
  };
};

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

const isLegacyStoredDraft = (value: unknown): value is LegacyStoredPlaytestDraft => {
  if (value === null || typeof value !== 'object') {
    return false;
  }
  return 'version' in value
    && (value.version === 1 || value.version === 2)
    && 'deckId' in value
    && typeof value.deckId === 'string'
    && 'state' in value
    && value.state !== null
    && typeof value.state === 'object';
};

const migrateDraft = (draft: MigratableStoredDraft): StoredPlaytestDraft => {
  const instances = normalizePileGroups(draft.state.instances.map((instance) => ensurePlaytestInstanceShape(instance)));
  const setupSnapshot = draft.state.setupSnapshot
    ? {
        instances: normalizePileGroups(
          draft.state.setupSnapshot.instances.map((instance) => ensurePlaytestInstanceShape(instance)),
        ),
      }
    : null;
  const phase: PlaytestPhase = draft.state.phase === 'play' ? 'play' : 'opening';

  return {
    ...draft,
    version: PLAYTEST_DRAFT_VERSION,
    state: {
      ...draft.state,
      phase,
      instances,
      openingSetup: draft.state.openingSetup ?? { ...EMPTY_OPENING_SETUP },
      setupSnapshot,
    },
  };
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
      if (isStoredDraft(parsed)) {
        return migrateDraft(parsed);
      }
      return isLegacyStoredDraft(parsed) ? migrateDraft(parsed) : null;
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
