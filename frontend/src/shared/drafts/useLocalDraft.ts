import { computed, shallowRef, type Ref } from 'vue';
import { useEventListener } from '@vueuse/core';
import { toast } from 'vue-sonner';
import {
  deckEditorDraftSlotToken,
  deckEditorDraftSlotTokensEqual,
  type StoredDraft,
  type RetiredDraft,
  type Attempt,
  type DraftSlot,
  type DraftStorage,
  type DraftStorageCodec,
} from './storage';
import { transitionDeckDraftPersistence, type DeckDraftPersistenceState } from './lifecycle';
export type DraftConflict<F, C, P> =
  | { kind: 'active-draft'; slot: Extract<DraftSlot<F, C, P>, { kind: 'draft' }> }
  | { kind: 'remote-deletion'; slot: Extract<DraftSlot<F, C, P>, { kind: 'empty' | 'retired' }> }
  | { kind: 'created-elsewhere'; slot: Extract<DraftSlot<F, C, P>, { kind: 'retired' }> };
type PersistResult = 'saved' | 'memory-only' | 'conflict' | 'paused';
export type LocalDraftOptions<F, C, P> = DraftStorageCodec<F, C, P> & {
  resourceLabel?: string;
  ownerId: string;
  enabled: boolean;
  form: F;
  cardLookup: Ref<Record<string, C>>;
  contentSignature: Ref<string>;
  emptyContentSignature: string;
  storage: DraftStorage<F, C, P>;
  build: (
    owner: string,
    draftId: string,
    form: F,
    cards: Record<string, C>,
    attempt: Attempt<P> | null,
  ) => StoredDraft<F, C, P>;
};
export const useLocalDraft = <F, C, P>(options: LocalDraftOptions<F, C, P>) => {
  type StoredDeckEditorDraft = StoredDraft<F, C, P>;
  type StoredCreateAttempt = Attempt<P>;
  type DeckEditorDraftSlot = DraftSlot<F, C, P>;
  type RetiredDeckEditorDraft = RetiredDraft;
  type DeckEditorDraftConflict = DraftConflict<F, C, P>;
  const draftContentSignature = (draft: StoredDeckEditorDraft): string =>
    JSON.stringify({
      draftId: draft.draftId,
      form: draft.form,
      cards: draft.cards,
      pendingCreateAttempt: draft.pendingCreateAttempt,
    });
  const storage = options.storage;
  const buildStoredDeckEditorDraft = options.build;
  const deckEditorDraftStorageKey = options.key;
  const parseDeckEditorDraftSlotValue = options.parse;
  const createDeckEditorDraftId = (): string => crypto.randomUUID();
  const persistenceState = shallowRef<DeckDraftPersistenceState>(
    options.enabled ? { status: 'checking' } : { status: 'synced' },
  );
  const pendingRecovery = shallowRef<StoredDeckEditorDraft | null>(null);
  const recoveryConflictCandidate = shallowRef<StoredDeckEditorDraft | null>(null);
  const conflict = shallowRef<DeckEditorDraftConflict | null>(null);
  const draftId = shallowRef(createDeckEditorDraftId());
  const observedSlot = shallowRef<DeckEditorDraftSlot>({ kind: 'empty' });
  const storedDraft = shallowRef<StoredDeckEditorDraft | null>(null);
  const knownRetirement = shallowRef<RetiredDeckEditorDraft | null>(null);
  const reportInfo = (message: string) => toast.info(message.replaceAll('deck', options.resourceLabel ?? 'deck'));
  let warningShown = false;
  let mutationQueue = Promise.resolve();

  const enqueueMutation = <Result>(operation: () => Promise<Result>): Promise<Result> => {
    const result = mutationQueue.then(operation);
    mutationQueue = result.then(
      () => undefined,
      () => undefined,
    );
    return result;
  };

  const setPersistenceState = (next: DeckDraftPersistenceState): void => {
    persistenceState.value = transitionDeckDraftPersistence(persistenceState.value, next);
  };

  const warnStorageUnavailable = (message: string): void => {
    if (warningShown) return;
    warningShown = true;
    toast.error(message.replaceAll('deck', options.resourceLabel ?? 'deck'));
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
    if (slot.kind === 'retired' && slot.marker.draftId === draftId.value) {
      knownRetirement.value = slot.marker;
    }
    if (pendingRecovery.value) {
      recoveryConflictCandidate.value = pendingRecovery.value;
      storedDraft.value = pendingRecovery.value;
      pendingRecovery.value = null;
    }
    observedSlot.value = slot;
    conflict.value = conflictFromSlot(slot);
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
    knownRetirement.value = null;
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
    const result = await enqueueMutation(async () => {
      if (persistenceState.value.status === 'conflict') {
        return { status: 'conflict' as const, slot: observedSlot.value };
      }
      return await storage.discard(options.ownerId, deckEditorDraftSlotToken(observedSlot.value));
    });
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
  ): Promise<PersistResult> =>
    await enqueueMutation(async () => {
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
      const effectiveAttempt =
        pendingCreateAttempt === undefined
          ? (storedDraft.value?.pendingCreateAttempt ?? null)
          : pendingCreateAttempt;
      if (
        options.contentSignature.value === options.emptyContentSignature &&
        effectiveAttempt === null
      ) {
        if (observedSlot.value.kind !== 'draft')
          return persistenceState.value.status === 'memory-only' ? 'memory-only' : 'saved';
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
      if (
        persistenceState.value.status === 'synced' &&
        storedDraft.value &&
        draftContentSignature(storedDraft.value) === draftContentSignature(nextDraft)
      ) {
        return 'saved';
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
      if (persistenceState.value.status === 'memory-only')
        setPersistenceState({ status: 'synced' });
      return 'saved';
    });

  const retireAfterCreation = (attemptDraftId: string, createdDeckId: string): void => {
    void enqueueMutation(async () => {
      if (
        !options.enabled ||
        persistenceState.value.status === 'conflict' ||
        observedSlot.value.kind !== 'draft' ||
        observedSlot.value.draft.draftId !== attemptDraftId
      ) {
        if (persistenceState.value.status === 'conflict') {
          reportInfo('A different local deck draft remains available in this browser.');
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
        reportInfo('A different local deck draft remains available in this browser.');
      }
    });
  };

  const discardAfterDeletedCreation = (attemptDraftId: string): void => {
    void enqueueMutation(async () => {
      if (
        !options.enabled ||
        persistenceState.value.status === 'conflict' ||
        observedSlot.value.kind !== 'draft' ||
        observedSlot.value.draft.draftId !== attemptDraftId
      )
        return;
      const result = await storage.discard(
        options.ownerId,
        deckEditorDraftSlotToken(observedSlot.value),
      );
      if (result.status === 'unavailable') {
        warnStorageUnavailable(
          'The deleted deck was confirmed, but its browser draft could not be removed.',
        );
      } else if (result.status === 'conflict') {
        reportInfo('A different local deck draft remains available in this browser.');
      }
    });
  };

  const discardActiveDraft = async (): Promise<boolean> => {
    const result = await enqueueMutation(async () => {
      if (persistenceState.value.status === 'conflict') {
        return { status: 'conflict' as const, slot: observedSlot.value };
      }
      return await storage.discard(options.ownerId, deckEditorDraftSlotToken(observedSlot.value));
    });
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
    if (conflict.value?.kind !== 'active-draft' || storedDraft.value?.pendingCreateAttempt)
      return null;
    const draft = conflict.value.slot.draft;
    conflict.value = null;
    recoveryConflictCandidate.value = null;
    knownRetirement.value = null;
    beginRecoveredDraft(draft);
    return draft;
  };

  const overwriteConflict = async (asNewDraft: boolean): Promise<boolean> => {
    if (!conflict.value) return false;
    if (conflict.value.kind === 'active-draft' && conflict.value.slot.draft.pendingCreateAttempt) {
      reportInfo(
        'The stored draft has an unconfirmed Create request. Load it before replacing it.',
      );
      return false;
    }
    const mustRekey = knownRetirement.value?.draftId === draftId.value;
    const shouldRekey = asNewDraft || mustRekey;
    if (shouldRekey && storedDraft.value?.pendingCreateAttempt && !mustRekey) return false;
    if (shouldRekey) draftId.value = createDeckEditorDraftId();
    const nextDraft = buildStoredDeckEditorDraft(
      options.ownerId,
      draftId.value,
      options.form,
      options.cardLookup.value,
      shouldRekey ? null : (storedDraft.value?.pendingCreateAttempt ?? null),
    );
    const expectedSlot = deckEditorDraftSlotToken(observedSlot.value);
    const result = await enqueueMutation(async () => await storage.save(nextDraft, expectedSlot));
    if (result.status === 'unavailable') {
      conflict.value = null;
      recoveryConflictCandidate.value = null;
      storedDraft.value = nextDraft;
      knownRetirement.value = null;
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
    knownRetirement.value = null;
    setPersistenceState({ status: 'synced' });
    return true;
  };

  const discardThisTab = (): boolean => {
    if (storedDraft.value?.pendingCreateAttempt) return false;
    conflict.value = null;
    recoveryConflictCandidate.value = null;
    storedDraft.value = null;
    knownRetirement.value = null;
    draftId.value = createDeckEditorDraftId();
    setPersistenceState({ status: 'synced' });
    return true;
  };

  const isCreateAttemptDurable = (
    attemptDraftId: string,
    pendingAttempt: StoredCreateAttempt,
  ): boolean => {
    if (
      persistenceState.value.status === 'memory-only' ||
      persistenceState.value.status === 'conflict'
    )
      return false;
    const result = storage.read(options.ownerId);
    if (result.status !== 'loaded' || result.slot.kind !== 'draft') return false;
    const durableAttempt = result.slot.draft.pendingCreateAttempt;
    return (
      result.slot.draft.draftId === attemptDraftId &&
      durableAttempt !== null &&
      durableAttempt.signature === pendingAttempt.signature &&
      durableAttempt.startedAt === pendingAttempt.startedAt &&
      JSON.stringify(durableAttempt.payload) === JSON.stringify(pendingAttempt.payload)
    );
  };

  const isCurrentContentDurable = (): boolean => {
    if (options.contentSignature.value === options.emptyContentSignature) return true;
    const result = storage.read(options.ownerId);
    return (
      result.status === 'loaded' &&
      result.slot.kind === 'draft' &&
      result.slot.draft.draftId === draftId.value &&
      JSON.stringify(result.slot.draft.form) === options.contentSignature.value
    );
  };

  if (options.enabled && typeof window !== 'undefined') {
    useEventListener(window, 'storage', (event: StorageEvent) => {
      if (event.key !== deckEditorDraftStorageKey(options.ownerId)) return;
      let slot: DeckEditorDraftSlot = { kind: 'empty' };
      if (event.newValue !== null) {
        try {
          slot = parseDeckEditorDraftSlotValue(
            JSON.parse(event.newValue) as unknown,
            options.ownerId,
          ) ?? { kind: 'empty' };
        } catch {
          slot = { kind: 'empty' };
        }
      }
      if (
        deckEditorDraftSlotTokensEqual(
          deckEditorDraftSlotToken(slot),
          deckEditorDraftSlotToken(observedSlot.value),
        )
      )
        return;
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
    isCreateAttemptDurable,
    isCurrentContentDurable,
  };
};
