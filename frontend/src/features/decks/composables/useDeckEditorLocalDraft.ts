import { computed, ref, type Ref } from 'vue';
import { useEventListener } from '@vueuse/core';
import { toast } from 'vue-sonner';
import type { DeckCardSummary } from '@/domain/decks/types';
import type { DeckForm } from '@/features/decks/composables/deckEditorDraftTypes';
import {
  buildStoredDeckEditorDraft,
  createDeckEditorDraftId,
  createDeckEditorLocalDraftStorage,
  deckEditorDraftSlotToken,
  deckEditorDraftSlotTokensEqual,
  deckEditorDraftStorageKey,
  parseDeckEditorDraftSlotValue,
  type DeckEditorDraftSlot,
  type StoredCreateAttempt,
  type StoredDeckEditorDraft,
} from '@/features/decks/utils/deckEditorLocalDraftStorage';
import {
  transitionDeckDraftPersistence,
  type DeckDraftPersistenceState,
} from '@/features/decks/utils/deckEditorLifecycle';

export type DeckEditorDraftConflict =
  | { kind: 'active-draft'; slot: Extract<DeckEditorDraftSlot, { kind: 'draft' }> }
  | {
      kind: 'remote-deletion';
      slot: Extract<DeckEditorDraftSlot, { kind: 'empty' | 'retired' }>;
    }
  | { kind: 'created-elsewhere'; slot: Extract<DeckEditorDraftSlot, { kind: 'retired' }> };

type PersistResult = 'saved' | 'memory-only' | 'conflict' | 'paused';

type UseDeckEditorLocalDraftOptions = {
  ownerId: string;
  enabled: boolean;
  form: DeckForm;
  cardLookup: Ref<Record<string, DeckCardSummary>>;
  contentSignature: Ref<string>;
  emptyContentSignature: string;
};

const draftContentSignature = (draft: StoredDeckEditorDraft): string => JSON.stringify({
  draftId: draft.draftId,
  form: draft.form,
  cards: draft.cards,
  pendingCreateAttempt: draft.pendingCreateAttempt,
});

export const useDeckEditorLocalDraft = (options: UseDeckEditorLocalDraftOptions) => {
  const storage = createDeckEditorLocalDraftStorage();
  const persistenceState = ref<DeckDraftPersistenceState>(
    options.enabled ? { status: 'checking' } : { status: 'synced' },
  );
  const pendingRecovery = ref<StoredDeckEditorDraft | null>(null);
  const recoveryConflictCandidate = ref<StoredDeckEditorDraft | null>(null);
  const conflict = ref<DeckEditorDraftConflict | null>(null);
  const draftId = ref(createDeckEditorDraftId());
  const observedSlot = ref<DeckEditorDraftSlot>({ kind: 'empty' });
  const storedDraft = ref<StoredDeckEditorDraft | null>(null);
  let warningShown = false;
  let mutationQueue = Promise.resolve();

  const enqueueMutation = <Result>(operation: () => Promise<Result>): Promise<Result> => {
    const result = mutationQueue.then(operation);
    mutationQueue = result.then(() => undefined, () => undefined);
    return result;
  };

  const setPersistenceState = (next: DeckDraftPersistenceState): void => {
    persistenceState.value = transitionDeckDraftPersistence(persistenceState.value, next);
  };

  const warnStorageUnavailable = (message: string): void => {
    if (warningShown) return;
    warningShown = true;
    toast.error(message);
  };

  const setMemoryOnly = (message: string): void => {
    setPersistenceState({ status: 'memory-only' });
    warnStorageUnavailable(message);
  };

  const conflictFromSlot = (slot: DeckEditorDraftSlot): DeckEditorDraftConflict => {
    if (slot.kind === 'draft') return { kind: 'active-draft', slot };
    if (slot.kind === 'retired' && slot.marker.draftId === draftId.value) {
      return { kind: 'created-elsewhere', slot };
    }
    if (slot.kind === 'retired') return { kind: 'remote-deletion', slot };
    return { kind: 'remote-deletion', slot };
  };

  const enterConflict = (slot: DeckEditorDraftSlot): void => {
    const existingCreatedElsewhere = conflict.value?.kind === 'created-elsewhere'
      ? conflict.value
      : null;
    if (pendingRecovery.value) {
      recoveryConflictCandidate.value = pendingRecovery.value;
      storedDraft.value = pendingRecovery.value;
      pendingRecovery.value = null;
    }
    observedSlot.value = slot;
    conflict.value = existingCreatedElsewhere ?? conflictFromSlot(slot);
    setPersistenceState({ status: 'conflict' });
  };

  const initialize = async (): Promise<void> => {
    if (!options.enabled) return;
    const result = storage.read(options.ownerId);
    if (result.status === 'unavailable') {
      setMemoryOnly('Local draft recovery is unavailable in this browser.');
      return;
    }
    observedSlot.value = result.slot;
    if (result.slot.kind === 'draft') {
      pendingRecovery.value = result.slot.draft;
      draftId.value = result.slot.draft.draftId;
      setPersistenceState({ status: 'recovery' });
      return;
    }
    setPersistenceState({ status: 'synced' });
  };

  const beginRecoveredDraft = (draft: StoredDeckEditorDraft): void => {
    pendingRecovery.value = null;
    recoveryConflictCandidate.value = null;
    storedDraft.value = draft;
    draftId.value = draft.draftId;
    observedSlot.value = { kind: 'draft', draft };
    if (persistenceState.value.status === 'conflict') {
      setPersistenceState({ status: 'recovery' });
    }
  };

  const completeRecovery = (): void => {
    if (persistenceState.value.status === 'recovery') {
      setPersistenceState({ status: 'synced' });
    }
  };

  const discardRecovery = async (): Promise<boolean> => {
    if (!pendingRecovery.value) return true;
    const result = await enqueueMutation(async () => await storage.discard(
      options.ownerId,
      deckEditorDraftSlotToken(observedSlot.value),
    ));
    if (result.status === 'unavailable') {
      warnStorageUnavailable('The local deck draft could not be removed from this browser.');
      return false;
    }
    if (result.status === 'conflict') {
      pendingRecovery.value = null;
      enterConflict(result.slot);
      return false;
    }
    pendingRecovery.value = null;
    storedDraft.value = null;
    observedSlot.value = { kind: 'empty' };
    draftId.value = createDeckEditorDraftId();
    setPersistenceState({ status: 'synced' });
    return true;
  };

  const persist = async (
    pendingCreateAttempt?: StoredCreateAttempt | null,
  ): Promise<PersistResult> => await enqueueMutation(async () => {
    if (!options.enabled) return 'paused';
    if (persistenceState.value.status === 'conflict') {
      if (pendingCreateAttempt !== undefined && storedDraft.value) {
        storedDraft.value = {
          ...storedDraft.value,
          pendingCreateAttempt,
        };
        if (recoveryConflictCandidate.value) {
          recoveryConflictCandidate.value = storedDraft.value;
        }
      }
      return 'paused';
    }
    if (['checking', 'recovery'].includes(persistenceState.value.status)) return 'paused';
    const effectiveAttempt = pendingCreateAttempt === undefined
      ? storedDraft.value?.pendingCreateAttempt ?? null
      : pendingCreateAttempt;
    if (options.contentSignature.value === options.emptyContentSignature && effectiveAttempt === null) {
      if (observedSlot.value.kind !== 'draft') return persistenceState.value.status === 'memory-only'
        ? 'memory-only'
        : 'saved';
      const result = await storage.discard(
        options.ownerId,
        deckEditorDraftSlotToken(observedSlot.value),
      );
      if (result.status === 'unavailable') {
        setMemoryOnly('This deck could not be saved to local browser storage.');
        return 'memory-only';
      }
      if (result.status === 'conflict') {
        enterConflict(result.slot);
        return 'conflict';
      }
      observedSlot.value = { kind: 'empty' };
      storedDraft.value = null;
      return 'saved';
    }
    const nextDraft = buildStoredDeckEditorDraft(
      options.ownerId,
      draftId.value,
      options.form,
      options.cardLookup.value,
      effectiveAttempt,
    );
    if (storedDraft.value && draftContentSignature(storedDraft.value) === draftContentSignature(nextDraft)) {
      return persistenceState.value.status === 'memory-only' ? 'memory-only' : 'saved';
    }
    const result = await storage.save(nextDraft, deckEditorDraftSlotToken(observedSlot.value));
    if (result.status === 'unavailable') {
      storedDraft.value = nextDraft;
      setMemoryOnly('This deck could not be saved to local browser storage.');
      return 'memory-only';
    }
    if (result.status === 'conflict') {
      enterConflict(result.slot);
      return 'conflict';
    }
    storedDraft.value = result.draft;
    observedSlot.value = { kind: 'draft', draft: result.draft };
    if (persistenceState.value.status === 'memory-only') setPersistenceState({ status: 'synced' });
    return 'saved';
  });

  const retireAfterCreation = (attemptDraftId: string, createdDeckId: string): void => {
    void enqueueMutation(async () => {
      if (
        !options.enabled
        || persistenceState.value.status === 'conflict'
        || observedSlot.value.kind !== 'draft'
        || observedSlot.value.draft.draftId !== attemptDraftId
      ) {
        if (persistenceState.value.status === 'conflict') {
          toast.info('A different local deck draft remains available in this browser.');
        }
        return;
      }
      const result = await storage.retire(
        options.ownerId,
        attemptDraftId,
        createdDeckId,
        deckEditorDraftSlotToken(observedSlot.value),
      );
      if (result.status === 'unavailable') {
        warnStorageUnavailable('The deck was created, but its browser draft could not be retired.');
      } else if (result.status === 'conflict') {
        toast.info('A different local deck draft remains available in this browser.');
      }
    });
  };

  const discardAfterDeletedCreation = (attemptDraftId: string): void => {
    void enqueueMutation(async () => {
      if (
        !options.enabled
        || persistenceState.value.status === 'conflict'
        || observedSlot.value.kind !== 'draft'
        || observedSlot.value.draft.draftId !== attemptDraftId
      ) return;
      const result = await storage.discard(
        options.ownerId,
        deckEditorDraftSlotToken(observedSlot.value),
      );
      if (result.status === 'unavailable') {
        warnStorageUnavailable('The deleted deck was confirmed, but its browser draft could not be removed.');
      } else if (result.status === 'conflict') {
        toast.info('A different local deck draft remains available in this browser.');
      }
    });
  };

  const discardActiveDraft = async (): Promise<boolean> => {
    const result = await enqueueMutation(async () => await storage.discard(
      options.ownerId,
      deckEditorDraftSlotToken(observedSlot.value),
    ));
    if (result.status === 'unavailable') {
      setMemoryOnly('The local deck draft could not be removed from this browser.');
      return false;
    }
    if (result.status === 'conflict') {
      enterConflict(result.slot);
      return false;
    }
    observedSlot.value = { kind: 'empty' };
    storedDraft.value = null;
    draftId.value = createDeckEditorDraftId();
    return true;
  };

  const loadConflictDraft = (): StoredDeckEditorDraft | null => {
    if (conflict.value?.kind !== 'active-draft' || storedDraft.value?.pendingCreateAttempt) return null;
    const draft = conflict.value.slot.draft;
    conflict.value = null;
    recoveryConflictCandidate.value = null;
    beginRecoveredDraft(draft);
    return draft;
  };

  const overwriteConflict = async (asNewDraft: boolean): Promise<boolean> => {
    if (!conflict.value) return false;
    if (asNewDraft && storedDraft.value?.pendingCreateAttempt) return false;
    if (asNewDraft) draftId.value = createDeckEditorDraftId();
    const nextDraft = buildStoredDeckEditorDraft(
      options.ownerId,
      draftId.value,
      options.form,
      options.cardLookup.value,
      asNewDraft ? null : storedDraft.value?.pendingCreateAttempt ?? null,
    );
    const result = await enqueueMutation(async () => await storage.save(
      nextDraft,
      deckEditorDraftSlotToken(observedSlot.value),
    ));
    if (result.status === 'unavailable') {
      conflict.value = null;
      recoveryConflictCandidate.value = null;
      storedDraft.value = nextDraft;
      setPersistenceState({ status: 'memory-only' });
      warnStorageUnavailable('This deck could not be saved to local browser storage.');
      return true;
    }
    if (result.status === 'conflict') {
      observedSlot.value = result.slot;
      conflict.value = conflictFromSlot(result.slot);
      return false;
    }
    storedDraft.value = result.draft;
    observedSlot.value = { kind: 'draft', draft: result.draft };
    conflict.value = null;
    recoveryConflictCandidate.value = null;
    setPersistenceState({ status: 'synced' });
    return true;
  };

  const discardThisTab = (): boolean => {
    if (storedDraft.value?.pendingCreateAttempt) return false;
    conflict.value = null;
    recoveryConflictCandidate.value = null;
    storedDraft.value = null;
    draftId.value = createDeckEditorDraftId();
    setPersistenceState({ status: 'synced' });
    return true;
  };

  if (options.enabled && typeof window !== 'undefined') {
    useEventListener(window, 'storage', (event: StorageEvent) => {
      if (event.key !== deckEditorDraftStorageKey(options.ownerId)) return;
      let slot: DeckEditorDraftSlot = { kind: 'empty' };
      if (event.newValue !== null) {
        try {
          slot = parseDeckEditorDraftSlotValue(JSON.parse(event.newValue) as unknown, options.ownerId)
            ?? { kind: 'empty' };
        } catch {
          slot = { kind: 'empty' };
        }
      }
      if (deckEditorDraftSlotTokensEqual(
        deckEditorDraftSlotToken(slot),
        deckEditorDraftSlotToken(observedSlot.value),
      )) return;
      enterConflict(slot);
    });
  }

  void initialize();

  return {
    persistenceState,
    pendingRecovery,
    recoveryConflictCandidate,
    conflict,
    draftId: computed(() => draftId.value),
    storageUnavailable: computed(() => persistenceState.value.status === 'memory-only'),
    beginRecoveredDraft,
    completeRecovery,
    discardRecovery,
    persist,
    retireAfterCreation,
    discardAfterDeletedCreation,
    discardActiveDraft,
    loadConflictDraft,
    overwriteConflict,
    discardThisTab,
  };
};
