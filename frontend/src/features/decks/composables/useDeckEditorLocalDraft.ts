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
  const conflict = ref<DeckEditorDraftConflict | null>(null);
  const draftId = ref(createDeckEditorDraftId());
  const observedSlot = ref<DeckEditorDraftSlot>({ kind: 'empty' });
  const storedDraft = ref<StoredDeckEditorDraft | null>(null);
  let warningShown = false;

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
    observedSlot.value = slot;
    conflict.value = conflictFromSlot(slot);
    setPersistenceState({ status: 'conflict' });
  };

  const initialize = (): void => {
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
    if (result.slot.kind === 'retired') {
      const discarded = storage.discard(options.ownerId, deckEditorDraftSlotToken(result.slot));
      if (discarded.status === 'unavailable') {
        setMemoryOnly('Local draft recovery is unavailable in this browser.');
        return;
      }
      if (discarded.status === 'conflict') {
        enterConflict(discarded.slot);
        return;
      }
      observedSlot.value = { kind: 'empty' };
    }
    setPersistenceState({ status: 'synced' });
  };

  const beginRecoveredDraft = (draft: StoredDeckEditorDraft): void => {
    pendingRecovery.value = null;
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

  const discardRecovery = (): boolean => {
    if (!pendingRecovery.value) return true;
    const result = storage.discard(options.ownerId, deckEditorDraftSlotToken(observedSlot.value));
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

  const persist = (pendingCreateAttempt?: StoredCreateAttempt | null): PersistResult => {
    if (!options.enabled) return 'paused';
    if (['checking', 'recovery', 'conflict'].includes(persistenceState.value.status)) return 'paused';
    const effectiveAttempt = pendingCreateAttempt === undefined
      ? storedDraft.value?.pendingCreateAttempt ?? null
      : pendingCreateAttempt;
    if (options.contentSignature.value === options.emptyContentSignature && effectiveAttempt === null) {
      if (observedSlot.value.kind !== 'draft') return persistenceState.value.status === 'memory-only'
        ? 'memory-only'
        : 'saved';
      const result = storage.discard(options.ownerId, deckEditorDraftSlotToken(observedSlot.value));
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
    const result = storage.save(nextDraft, deckEditorDraftSlotToken(observedSlot.value));
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
  };

  const retireAfterCreation = (createdDeckId: string): void => {
    if (
      !options.enabled
      || persistenceState.value.status === 'conflict'
      || observedSlot.value.kind !== 'draft'
      || observedSlot.value.draft.draftId !== draftId.value
    ) {
      if (persistenceState.value.status === 'conflict') {
        toast.info('A different local deck draft remains available in this browser.');
      }
      return;
    }
    const result = storage.retire(
      options.ownerId,
      draftId.value,
      createdDeckId,
      deckEditorDraftSlotToken(observedSlot.value),
    );
    if (result.status === 'unavailable') {
      warnStorageUnavailable('The deck was created, but its browser draft could not be retired.');
    } else if (result.status === 'conflict') {
      toast.info('A different local deck draft remains available in this browser.');
    }
  };

  const discardActiveDraft = (): boolean => {
    const result = storage.discard(options.ownerId, deckEditorDraftSlotToken(observedSlot.value));
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
    if (conflict.value?.kind !== 'active-draft') return null;
    const draft = conflict.value.slot.draft;
    conflict.value = null;
    beginRecoveredDraft(draft);
    return draft;
  };

  const overwriteConflict = (asNewDraft: boolean): boolean => {
    if (!conflict.value) return false;
    if (asNewDraft) draftId.value = createDeckEditorDraftId();
    const nextDraft = buildStoredDeckEditorDraft(
      options.ownerId,
      draftId.value,
      options.form,
      options.cardLookup.value,
    );
    const result = storage.save(nextDraft, deckEditorDraftSlotToken(observedSlot.value));
    if (result.status === 'unavailable') {
      conflict.value = null;
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
    setPersistenceState({ status: 'synced' });
    return true;
  };

  const discardThisTab = (): void => {
    conflict.value = null;
    storedDraft.value = null;
    draftId.value = createDeckEditorDraftId();
    setPersistenceState({ status: 'synced' });
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

  initialize();

  return {
    persistenceState,
    pendingRecovery,
    conflict,
    draftId: computed(() => draftId.value),
    storageUnavailable: computed(() => persistenceState.value.status === 'memory-only'),
    beginRecoveredDraft,
    completeRecovery,
    discardRecovery,
    persist,
    retireAfterCreation,
    discardActiveDraft,
    loadConflictDraft,
    overwriteConflict,
    discardThisTab,
  };
};
