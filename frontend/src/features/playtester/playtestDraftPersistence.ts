import type { DeckRecord } from '@/domain/decks/types';
import type {
  PlaytestOpeningSetup,
  PlaytestOpeningStep,
  PlaytestCardInstance,
  PlaytestState,
  StoredPlaytestDraft,
} from '@/features/playtester/types';
import {
  EMPTY_OPENING_SETUP,
  normalizeInstanceFields,
  normalizePileGroups,
  PLAYTEST_DRAFT_VERSION,
  renumberAllZones,
  setupCardIds,
  syncOpeningSelections,
  uniqueIds,
  type LegacyPlaytestCardInstance,
} from '@/features/playtester/playtestStateCore';

export const serializePlaytestDraft = (state: PlaytestState): StoredPlaytestDraft => ({
  version: PLAYTEST_DRAFT_VERSION,
  deckId: state.deckId,
  deckUpdatedAt: state.deckUpdatedAt,
  state: {
    ...state,
    instances: normalizePileGroups(state.instances),
    openingSetup: syncOpeningSelections(state).openingSetup,
    setupSnapshot: state.setupSnapshot
      ? { instances: normalizePileGroups(state.setupSnapshot.instances) }
      : null,
  },
  savedAt: new Date().toISOString(),
});

type LegacyPlaytestOpeningSetup = Omit<PlaytestOpeningSetup, 'handledSetupCardIds' | 'mulliganCount' | 'step'> & {
  handledSetupCardIds?: string[];
  mulliganCount?: number;
  step?: PlaytestOpeningStep;
};

type LegacyPlaytestState = Omit<PlaytestState, 'instances' | 'setupSnapshot' | 'openingSetup'> & {
  openingSetup: LegacyPlaytestOpeningSetup;
  instances: LegacyPlaytestCardInstance[];
  setupSnapshot: null | { instances: LegacyPlaytestCardInstance[] };
};

type LegacyStoredPlaytestDraft = Omit<StoredPlaytestDraft, 'version' | 'state'> & {
  version: 1 | 2;
  state: LegacyPlaytestState;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object';

const isOpeningStep = (value: unknown): value is PlaytestOpeningStep =>
  value === 'mana' || value === 'setup' || value === 'hand';

const migratedOpeningStep = (
  state: LegacyPlaytestState,
  instances: PlaytestCardInstance[],
): PlaytestOpeningStep => {
  if (isOpeningStep(state.openingSetup.step)) {
    return state.openingSetup.step;
  }
  if (
    state.phase === 'opening'
    && state.openingSetup.selectedManaInstanceIds.length > 0
    && instances.some((instance) => instance.zoneId === 'hand')
  ) {
    return 'hand';
  }
  return 'mana';
};

const migrateOpeningStepInstances = (
  state: LegacyPlaytestState,
  instances: PlaytestCardInstance[],
  step: PlaytestOpeningStep,
): PlaytestCardInstance[] => {
  if (state.phase !== 'opening' || step === 'hand') {
    return instances;
  }
  return instances.map((instance) =>
    instance.zoneId === 'hand'
      ? {
          ...instance,
          zoneId: 'library',
          tapped: false,
          boardX: null,
          boardY: null,
          pileGroupId: null,
          pileOrder: null,
        }
      : instance,
  );
};

const migratePlaytestState = (state: LegacyPlaytestState): PlaytestState => {
  const normalizedInstances = normalizePileGroups(renumberAllZones(state.instances.map(normalizeInstanceFields)));
  const step = migratedOpeningStep(state, normalizedInstances);
  const instances = normalizePileGroups(renumberAllZones(migrateOpeningStepInstances(state, normalizedInstances, step)));
  return {
    ...state,
    openingSetup: {
      ...EMPTY_OPENING_SETUP,
      ...state.openingSetup,
      step,
      handledSetupCardIds: uniqueIds(state.openingSetup.handledSetupCardIds ?? [])
        .filter((cardId) => setupCardIds(instances).has(cardId)),
    },
    instances,
    setupSnapshot: state.setupSnapshot
      ? { instances: normalizePileGroups(renumberAllZones(state.setupSnapshot.instances.map(normalizeInstanceFields))) }
      : null,
  };
};

export const migrateStoredPlaytestDraft = (value: unknown): StoredPlaytestDraft | null => {
  if (!isRecord(value)) {
    return null;
  }
  if (value.version !== 1 && value.version !== PLAYTEST_DRAFT_VERSION) {
    return null;
  }
  if (typeof value.deckId !== 'string' || !isRecord(value.state)) {
    return null;
  }
  if (!Array.isArray(value.state.instances)) {
    return null;
  }

  const legacyDraft = value as unknown as LegacyStoredPlaytestDraft;
  return {
    ...legacyDraft,
    version: PLAYTEST_DRAFT_VERSION,
    deckUpdatedAt: typeof legacyDraft.deckUpdatedAt === 'string' ? legacyDraft.deckUpdatedAt : '',
    savedAt: typeof legacyDraft.savedAt === 'string' ? legacyDraft.savedAt : new Date(0).toISOString(),
    state: migratePlaytestState(legacyDraft.state),
  };
};

export const isStoredDraftStale = (draft: StoredPlaytestDraft, deck: DeckRecord): boolean =>
  draft.deckUpdatedAt !== deck.updated_at;
