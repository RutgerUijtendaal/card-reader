import { computed, ref, type Ref } from 'vue';
import { isAxiosError } from 'axios';
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
  persistAttempt: (
    attempt: StoredCreateAttempt | null,
  ) => Promise<'saved' | 'memory-only' | 'conflict' | 'paused'>;
  retireAfterCreation: (attemptDraftId: string, createdDeckId: string) => void;
  discardAfterDeletedCreation: (attemptDraftId: string) => void;
  onSuccess: (record: DeckRecord, attempt: CreateAttempt) => Promise<void>;
  onDeleted: (attempt: CreateAttempt) => Promise<void>;
};

export type PendingCreateResolution = 'created' | 'deleted' | 'unknown';

const AMBIGUOUS_CREATE_LOOKUP_DELAYS_MS = [0, 250, 750, 2_000] as const;
const AMBIGUOUS_CLIENT_RESPONSE_STATUSES = new Set([408, 499]);

const wait = async (delayMs: number): Promise<void> => {
  if (delayMs === 0) return;
  await new Promise<void>((resolve) => {
    globalThis.setTimeout(resolve, delayMs);
  });
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

const isDefinitiveCreateRejection = (error: unknown): boolean => {
  if (!isAxiosError(error) || error.response === undefined) return false;
  const { status } = error.response;
  return status >= 400
    && status < 500
    && !AMBIGUOUS_CLIENT_RESPONSE_STATUSES.has(status);
};

export const useDeckEditorPublication = (options: UseDeckEditorPublicationOptions) => {
  const creationState = ref<DeckCreationState>({ status: 'idle' });
  const attempt = ref<CreateAttempt | null>(null);
  const terminalNavigationRetry = ref<(() => Promise<void>) | null>(null);
  const terminalNavigationInFlight = ref(false);
  let publicationSucceeded = false;

  const setCreationState = (next: DeckCreationState): void => {
    creationState.value = transitionDeckCreation(creationState.value, next);
  };

  const runTerminalNavigation = async (errorMessage: string): Promise<void> => {
    const navigation = terminalNavigationRetry.value;
    if (!navigation || terminalNavigationInFlight.value) return;
    terminalNavigationInFlight.value = true;
    try {
      await navigation();
      if (terminalNavigationRetry.value === navigation) terminalNavigationRetry.value = null;
    } catch {
      toast.error(errorMessage);
    } finally {
      terminalNavigationInFlight.value = false;
    }
  };

  const completeSuccess = async (record: DeckRecord, currentAttempt: CreateAttempt): Promise<void> => {
    if (publicationSucceeded) return;
    publicationSucceeded = true;
    options.retireAfterCreation(currentAttempt.draftId, record.id);
    terminalNavigationRetry.value = async () => await options.onSuccess(record, currentAttempt);
    try {
      await runTerminalNavigation(
        'The deck was created, but its editor could not be opened. Click Continue to try again.',
      );
    } finally {
      if (creationState.value.status === 'creating' || creationState.value.status === 'unknown') {
        setCreationState({ status: 'idle' });
      }
    }
  };

  const completeDeleted = async (currentAttempt: CreateAttempt): Promise<void> => {
    if (publicationSucceeded) return;
    publicationSucceeded = true;
    options.discardAfterDeletedCreation(currentAttempt.draftId);
    terminalNavigationRetry.value = async () => await options.onDeleted(currentAttempt);
    try {
      await runTerminalNavigation(
        'The deleted deck was confirmed, but navigation failed. Click Continue to try again.',
      );
    } finally {
      if (creationState.value.status === 'creating' || creationState.value.status === 'unknown') {
        setCreationState({ status: 'idle' });
      }
    }
  };

  const lookupAttempt = async (
    currentAttempt: CreateAttempt,
    delays: readonly number[],
  ): Promise<
    | { status: 'found'; record: DeckRecord }
    | { status: 'deleted' }
    | { status: 'missing' }
    | { status: 'unknown' }
  > => {
    let lookupFailed = false;
    for (const delayMs of delays) {
      await wait(delayMs);
      try {
        const result = await fetchMyDeckByCreationKey(currentAttempt.draftId);
        if (result.status === 'found' || result.status === 'deleted') return result;
      } catch {
        lookupFailed = true;
      }
    }
    return lookupFailed ? { status: 'unknown' } : { status: 'missing' };
  };

  const clearAttemptAfterDefinitiveFailure = async (): Promise<void> => {
    attempt.value = null;
    setCreationState({ status: 'idle' });
    await options.persistAttempt(null);
    toast.error('The deck could not be created. Your local draft is still available.');
  };

  const resolveFailedRequest = async (
    currentAttempt: CreateAttempt,
    requestError: unknown,
  ): Promise<void> => {
    setCreationState({ status: 'unknown', reconciliation: 'checking' });
    const requestDefinitelyFinished = isDefinitiveCreateRejection(requestError);
    const lookup = await lookupAttempt(
      currentAttempt,
      requestDefinitelyFinished ? [0] : AMBIGUOUS_CREATE_LOOKUP_DELAYS_MS,
    );
    if (lookup.status === 'found') {
      await completeSuccess(lookup.record, currentAttempt);
      return;
    }
    if (lookup.status === 'deleted') {
      await completeDeleted(currentAttempt);
      return;
    }
    if (lookup.status === 'missing' && requestDefinitelyFinished) {
      await clearAttemptAfterDefinitiveFailure();
      return;
    }
    setCreationState({ status: 'unknown', reconciliation: 'awaiting-retry' });
    toast.error('Creation could not be confirmed. Retry will safely use the same deck request.');
  };

  const executeAttempt = async (currentAttempt: CreateAttempt): Promise<void> => {
    let result: Awaited<ReturnType<typeof createDeck>>;
    try {
      result = await createDeck(currentAttempt.payload, currentAttempt.draftId);
    } catch (error) {
      await resolveFailedRequest(currentAttempt, error);
      return;
    }
    await completeSuccess(result.record, currentAttempt);
  };

  const create = async (): Promise<void> => {
    if (creationState.value.status !== 'idle') return;
    if (publicationSucceeded) {
      await runTerminalNavigation(
        'The confirmed deck outcome could not be opened. Click Continue to try again.',
      );
      return;
    }
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
    const persistResult = await options.persistAttempt(storedAttempt(currentAttempt));
    if (persistResult === 'conflict' || persistResult === 'paused') return;
    attempt.value = currentAttempt;
    setCreationState({ status: 'creating' });
    await executeAttempt(currentAttempt);
  };

  const retry = async (): Promise<void> => {
    if (creationState.value.status !== 'unknown' || !attempt.value || publicationSucceeded) return;
    const currentAttempt = attempt.value;
    await options.persistAttempt(storedAttempt(currentAttempt));
    setCreationState({ status: 'creating' });
    await executeAttempt(currentAttempt);
  };

  const persistCurrentAttempt = async (): Promise<void> => {
    if (!attempt.value) return;
    await options.persistAttempt(storedAttempt(attempt.value));
  };

  const recoverPendingAttempt = async (
    pending: StoredCreateAttempt,
  ): Promise<PendingCreateResolution> => {
    if (publicationSucceeded) return 'created';
    if (creationState.value.status !== 'idle') return 'unknown';
    const recoveredAttempt = immutableAttempt(
      options.draftId.value,
      pending.payload,
      pending.signature,
      pending.startedAt,
    );
    attempt.value = recoveredAttempt;
    setCreationState({ status: 'unknown', reconciliation: 'checking' });
    const lookup = await lookupAttempt(recoveredAttempt, AMBIGUOUS_CREATE_LOOKUP_DELAYS_MS);
    if (lookup.status === 'found') {
      await completeSuccess(lookup.record, recoveredAttempt);
      return 'created';
    }
    if (lookup.status === 'deleted') {
      await completeDeleted(recoveredAttempt);
      return 'deleted';
    }
    setCreationState({ status: 'unknown', reconciliation: 'awaiting-retry' });
    toast.error('Creation could not be confirmed. Retry will safely use the same deck request.');
    return 'unknown';
  };

  return {
    creationState,
    attempt,
    hasTerminalNavigationRetry: computed(() => terminalNavigationRetry.value !== null),
    terminalNavigationInFlight: computed(() => terminalNavigationInFlight.value),
    isCreating: computed(() => creationState.value.status === 'creating'),
    isCreationUnknown: computed(() => creationState.value.status === 'unknown'),
    isReconciling: computed(
      () => creationState.value.status === 'unknown'
        && creationState.value.reconciliation === 'checking',
    ),
    create,
    retry,
    persistCurrentAttempt,
    recoverPendingAttempt,
  };
};
