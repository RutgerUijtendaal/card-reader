import { computed, ref, type Ref } from 'vue';
import { toast } from 'vue-sonner';
import {
  createDeck,
  fetchMyDeckByCreationKey,
} from '@/domain/decks/api';
import type { DeckRecord, DeckUpsertRequest } from '@/domain/decks/types';
import type { StoredCreateAttempt } from '@/features/decks/utils/deckEditorLocalDraftStorage';
import {
  canCreateFromPersistenceState,
  transitionDeckCreation,
  type DeckCreationState,
  type DeckDraftPersistenceState,
} from '@/features/decks/utils/deckEditorLifecycle';

export type CreateAttempt = Readonly<{
  draftId: string;
  payload: DeckUpsertRequest;
  signature: string;
  startedAt: string;
}>;

type UseDeckEditorPublicationOptions = {
  persistenceState: Ref<DeckDraftPersistenceState>;
  draftId: Ref<string>;
  payloadSignature: Ref<string>;
  buildPayload: () => DeckUpsertRequest;
  validate: () => Promise<boolean>;
  persistAttempt: (attempt: StoredCreateAttempt | null) => 'saved' | 'memory-only' | 'conflict' | 'paused';
  retireAfterCreation: (createdDeckId: string) => void;
  onSuccess: (record: DeckRecord, attempt: CreateAttempt) => Promise<void>;
};

const clonePayload = (payload: DeckUpsertRequest): DeckUpsertRequest => ({
  ...payload,
  entries: payload.entries.map((entry) => ({ ...entry })),
  sideboards: payload.sideboards.map((sideboard) => ({
    ...sideboard,
    entries: sideboard.entries.map((entry) => ({ ...entry })),
  })),
  tag_ids: [...payload.tag_ids],
  suggested_type_labels: [...payload.suggested_type_labels],
});

const storedAttempt = (attempt: CreateAttempt): StoredCreateAttempt => ({
  payload: clonePayload(attempt.payload),
  signature: attempt.signature,
  startedAt: attempt.startedAt,
});

const immutableAttempt = (
  draftId: string,
  payload: DeckUpsertRequest,
  signature: string,
  startedAt: string,
): CreateAttempt => {
  const clonedPayload = clonePayload(payload);
  clonedPayload.entries.forEach(Object.freeze);
  clonedPayload.sideboards.forEach((sideboard) => {
    sideboard.entries.forEach(Object.freeze);
    Object.freeze(sideboard.entries);
    Object.freeze(sideboard);
  });
  Object.freeze(clonedPayload.entries);
  Object.freeze(clonedPayload.sideboards);
  Object.freeze(clonedPayload.tag_ids);
  Object.freeze(clonedPayload.suggested_type_labels);
  Object.freeze(clonedPayload);
  return Object.freeze({ draftId, payload: clonedPayload, signature, startedAt });
};

export const useDeckEditorPublication = (options: UseDeckEditorPublicationOptions) => {
  const creationState = ref<DeckCreationState>({ status: 'idle' });
  const attempt = ref<CreateAttempt | null>(null);
  let publicationSucceeded = false;

  const setCreationState = (next: DeckCreationState): void => {
    creationState.value = transitionDeckCreation(creationState.value, next);
  };

  const completeSuccess = async (record: DeckRecord, currentAttempt: CreateAttempt): Promise<void> => {
    if (publicationSucceeded) return;
    publicationSucceeded = true;
    options.retireAfterCreation(record.id);
    try {
      await options.onSuccess(record, currentAttempt);
    } finally {
      if (creationState.value.status === 'creating' || creationState.value.status === 'unknown') {
        setCreationState({ status: 'idle' });
      }
    }
  };

  const resolveFailedRequest = async (currentAttempt: CreateAttempt): Promise<void> => {
    try {
      const record = await fetchMyDeckByCreationKey(currentAttempt.draftId);
      if (record) {
        await completeSuccess(record, currentAttempt);
        return;
      }
      attempt.value = null;
      setCreationState({ status: 'idle' });
      options.persistAttempt(null);
      toast.error('The deck could not be created. Your local draft is still available.');
    } catch {
      setCreationState({ status: 'unknown' });
      toast.error('Creation could not be confirmed. Retry will safely use the same deck request.');
    }
  };

  const executeAttempt = async (currentAttempt: CreateAttempt): Promise<void> => {
    try {
      const result = await createDeck(currentAttempt.payload, currentAttempt.draftId);
      await completeSuccess(result.record, currentAttempt);
    } catch {
      await resolveFailedRequest(currentAttempt);
    }
  };

  const create = async (): Promise<void> => {
    if (creationState.value.status !== 'idle' || publicationSucceeded) return;
    if (!canCreateFromPersistenceState(options.persistenceState.value)) {
      toast.error('Resolve the local draft conflict before creating this deck.');
      return;
    }
    if (!await options.validate()) return;
    const currentAttempt = immutableAttempt(
      options.draftId.value,
      options.buildPayload(),
      options.payloadSignature.value,
      new Date().toISOString(),
    );
    const persistResult = options.persistAttempt(storedAttempt(currentAttempt));
    if (persistResult === 'conflict' || persistResult === 'paused') return;
    attempt.value = currentAttempt;
    setCreationState({ status: 'creating' });
    await executeAttempt(currentAttempt);
  };

  const retry = async (): Promise<void> => {
    if (creationState.value.status !== 'unknown' || !attempt.value || publicationSucceeded) return;
    const currentAttempt = attempt.value;
    setCreationState({ status: 'creating' });
    await executeAttempt(currentAttempt);
  };

  const recoverPendingAttempt = async (pending: StoredCreateAttempt): Promise<void> => {
    if (publicationSucceeded || creationState.value.status !== 'idle') return;
    const recoveredAttempt = immutableAttempt(
      options.draftId.value,
      pending.payload,
      pending.signature,
      pending.startedAt,
    );
    attempt.value = recoveredAttempt;
    setCreationState({ status: 'unknown' });
    try {
      const record = await fetchMyDeckByCreationKey(recoveredAttempt.draftId);
      if (record) {
        await completeSuccess(record, recoveredAttempt);
        return;
      }
      attempt.value = null;
      setCreationState({ status: 'idle' });
      options.persistAttempt(null);
    } catch {
      toast.error('Creation could not be confirmed. Retry will safely use the same deck request.');
    }
  };

  return {
    creationState,
    attempt,
    isCreating: computed(() => creationState.value.status === 'creating'),
    isCreationUnknown: computed(() => creationState.value.status === 'unknown'),
    create,
    retry,
    recoverPendingAttempt,
  };
};
