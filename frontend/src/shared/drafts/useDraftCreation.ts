import { computed, shallowRef, ref, type Ref } from 'vue';
import { isAxiosError } from 'axios';
import { toast } from 'vue-sonner';
import type { Attempt } from './storage';
import {
  canCreateFromPersistenceState,
  transitionDeckCreation,
  type DeckCreationState,
  type DeckDraftPersistenceState,
} from './lifecycle';
export type CreateAttempt<P> = Readonly<{
  draftId: string;
  payload: P;
  signature: string;
  startedAt: string;
}>;

export type DraftCreationOptions<P, R> = {
  resourceLabel?: string;
  createRequest: (payload: P, key: string) => Promise<{ record: R }>;
  lookupRequest: (
    key: string,
  ) => Promise<{ status: 'found'; record: R } | { status: 'deleted' | 'missing' }>;
  persistenceState: Ref<DeckDraftPersistenceState>;
  draftId: Ref<string>;
  payloadSignature: Ref<string>;
  buildPayload: () => P;
  validate: () => Promise<boolean>;
  persistAttempt: (
    attempt: Attempt<P> | null,
  ) => Promise<'saved' | 'memory-only' | 'conflict' | 'paused'>;
  retireAfterCreation: (attemptDraftId: string, createdDeckId: string) => void;
  discardAfterDeletedCreation: (attemptDraftId: string) => void;
  onSuccess: (record: R, attempt: CreateAttempt<P>) => Promise<void>;
  onDeleted: (attempt: CreateAttempt<P>) => Promise<void>;
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

const isDefinitiveCreateRejection = (error: unknown): boolean => {
  if (!isAxiosError(error) || error.response === undefined) return false;
  const { status } = error.response;
  return status >= 400 && status < 500 && !AMBIGUOUS_CLIENT_RESPONSE_STATUSES.has(status);
};

export const useDraftCreation = <P, R extends { id: string }>(
  options: DraftCreationOptions<P, R>,
) => {
  const reportError = (message: string) =>
    toast.error(message.replaceAll('deck', options.resourceLabel ?? 'deck'));
  const clonePayload = (payload: P): P => JSON.parse(JSON.stringify(payload)) as P;
  const storedAttempt = (attempt: CreateAttempt<P>): Attempt<P> => ({
    payload: clonePayload(attempt.payload),
    signature: attempt.signature,
    startedAt: attempt.startedAt,
  });
  const freeze = (value: unknown): void => {
    if (value && typeof value === 'object') {
      Object.values(value).forEach(freeze);
      Object.freeze(value);
    }
  };
  const immutableAttempt = (
    draftId: string,
    payload: P,
    signature: string,
    startedAt: string,
  ): CreateAttempt<P> => {
    const cloned = clonePayload(payload);
    freeze(cloned);
    return Object.freeze({ draftId, payload: cloned, signature, startedAt });
  };
  const creationState = shallowRef<DeckCreationState>({ status: 'idle' });
  const attempt = shallowRef<CreateAttempt<P> | null>(null);
  const terminalNavigationRetry = shallowRef<(() => Promise<void>) | null>(null);
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
      reportError(errorMessage);
    } finally {
      terminalNavigationInFlight.value = false;
    }
  };

  const completeSuccess = async (record: R, currentAttempt: CreateAttempt<P>): Promise<void> => {
    if (publicationSucceeded) return;
    publicationSucceeded = true;
    try {
      options.retireAfterCreation(currentAttempt.draftId, record.id);
    } catch {
      reportError('The deck was created, but its browser draft could not be retired.');
    }
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

  const completeDeleted = async (currentAttempt: CreateAttempt<P>): Promise<void> => {
    if (publicationSucceeded) return;
    publicationSucceeded = true;
    try {
      options.discardAfterDeletedCreation(currentAttempt.draftId);
    } catch {
      reportError('The deleted deck was confirmed, but its browser draft could not be removed.');
    }
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
    currentAttempt: CreateAttempt<P>,
    delays: readonly number[],
  ): Promise<
    | { status: 'found'; record: R }
    | { status: 'deleted' }
    | { status: 'missing' }
    | { status: 'unknown' }
  > => {
    let lookupFailed = false;
    for (const delayMs of delays) {
      await wait(delayMs);
      try {
        const result = await options.lookupRequest(currentAttempt.draftId);
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
    reportError('The deck could not be created. Your local draft is still available.');
  };

  const resolveFailedRequest = async (
    currentAttempt: CreateAttempt<P>,
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
    reportError('Creation could not be confirmed. Retry will safely use the same request.');
  };

  const executeAttempt = async (currentAttempt: CreateAttempt<P>): Promise<void> => {
    let result: { record: R };
    try {
      result = await options.createRequest(currentAttempt.payload, currentAttempt.draftId);
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
      reportError('Resolve the local draft conflict before creating this deck.');
      return;
    }
    if (!(await options.validate())) return;
    if (creationState.value.status !== 'idle') return;
    setCreationState({ status: 'creating' });
    const currentAttempt = immutableAttempt(
      options.draftId.value,
      options.buildPayload(),
      options.payloadSignature.value,
      new Date().toISOString(),
    );
    attempt.value = currentAttempt;
    const persistResult = await options.persistAttempt(storedAttempt(currentAttempt));
    if (persistResult === 'conflict' || persistResult === 'paused') {
      attempt.value = null;
      setCreationState({ status: 'idle' });
      return;
    }
    await executeAttempt(currentAttempt);
  };

  const retry = async (): Promise<void> => {
    if (creationState.value.status !== 'unknown' || !attempt.value || publicationSucceeded) return;
    const currentAttempt = attempt.value;
    setCreationState({ status: 'creating' });
    await options.persistAttempt(storedAttempt(currentAttempt));
    await executeAttempt(currentAttempt);
  };

  const persistCurrentAttempt = async (): Promise<void> => {
    if (!attempt.value) return;
    await options.persistAttempt(storedAttempt(attempt.value));
  };

  const recoverPendingAttempt = async (pending: Attempt<P>): Promise<PendingCreateResolution> => {
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
    reportError('Creation could not be confirmed. Retry will safely use the same request.');
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
      () =>
        creationState.value.status === 'unknown' &&
        creationState.value.reconciliation === 'checking',
    ),
    create,
    retry,
    persistCurrentAttempt,
    recoverPendingAttempt,
  };
};
