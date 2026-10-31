export type Attempt<P> = { payload: P; signature: string; startedAt: string };
export type StoredDraft<F, C, P> = {
  version: 2;
  kind: 'draft';
  ownerId: string;
  draftId: string;
  revision: string;
  savedAt: string;
  form: F;
  cards: Record<string, C>;
  pendingCreateAttempt: Attempt<P> | null;
};
export type RetiredDraft = {
  version: 2;
  kind: 'retired';
  ownerId: string;
  draftId: string;
  revision: string;
  retiredAt: string;
  createdDeckId: string;
};
export type DraftSlot<F, C, P> =
  | { kind: 'empty' }
  | { kind: 'draft'; draft: StoredDraft<F, C, P> }
  | { kind: 'retired'; marker: RetiredDraft };
export type SlotToken = { kind: 'empty' } | { kind: 'draft' | 'retired'; revision: string };
export type ReadResult<F, C, P> =
  | { status: 'loaded'; slot: DraftSlot<F, C, P> }
  | { status: 'unavailable' };
export type SaveResult<F, C, P> =
  | { status: 'saved'; draft: StoredDraft<F, C, P> }
  | { status: 'conflict'; slot: DraftSlot<F, C, P> }
  | { status: 'unavailable' };
export type MutationResult<F, C, P> =
  | { status: 'empty' }
  | { status: 'retired'; marker: RetiredDraft }
  | { status: 'conflict'; slot: DraftSlot<F, C, P> }
  | { status: 'unavailable' };
export type DraftStorage<F, C, P> = {
  read: (owner: string) => ReadResult<F, C, P>;
  save: (draft: StoredDraft<F, C, P>, expected: SlotToken) => Promise<SaveResult<F, C, P>>;
  discard: (owner: string, expected: SlotToken) => Promise<MutationResult<F, C, P>>;
  retire: (
    owner: string,
    draftId: string,
    resourceId: string,
    expected: SlotToken,
  ) => Promise<MutationResult<F, C, P>>;
};
export type DraftStorageCodec<F, C, P> = {
  key: (owner: string) => string;
  parse: (value: unknown, owner: string) => DraftSlot<F, C, P> | null;
};
export type DraftLockManager = {
  request: <R>(
    name: string,
    options: { mode: 'exclusive' },
    callback: () => R | PromiseLike<R>,
  ) => Promise<R>;
};
export const deckEditorDraftSlotToken = <F, C, P>(slot: DraftSlot<F, C, P>): SlotToken => {
  if (slot.kind === 'draft') return { kind: 'draft', revision: slot.draft.revision };
  if (slot.kind === 'retired') return { kind: 'retired', revision: slot.marker.revision };
  return { kind: 'empty' };
};
export const deckEditorDraftSlotTokensEqual = (left: SlotToken, right: SlotToken): boolean =>
  left.kind === right.kind &&
  (left.kind === 'empty' || (right.kind !== 'empty' && left.revision === right.revision));
const resolveBrowserStorage = (): Storage | null => {
  try {
    return typeof globalThis.localStorage === 'undefined' ? null : globalThis.localStorage;
  } catch {
    return null;
  }
};

const resolveBrowserLockManager = (): DraftLockManager | null => {
  try {
    if (typeof globalThis.navigator === 'undefined' || !globalThis.navigator.locks) return null;
    return globalThis.navigator.locks;
  } catch {
    return null;
  }
};

export const createDraftStorage = <Form, Card, Payload>(
  codec: DraftStorageCodec<Form, Card, Payload>,
  storage?: Storage | null,
  lockManager?: DraftLockManager | null,
): DraftStorage<Form, Card, Payload> => {
  type DeckEditorDraftReadResult = ReadResult<Form, Card, Payload>;
  type DeckEditorDraftSaveResult = SaveResult<Form, Card, Payload>;
  type DeckEditorDraftMutationResult = MutationResult<Form, Card, Payload>;
  const deckEditorDraftStorageKey = codec.key;
  const parseDeckEditorDraftSlotValue = codec.parse;
  const deckEditorDraftLockName = (ownerId: string) => `${codec.key(ownerId)}.mutation`;

  const resolvedStorage = storage === undefined ? resolveBrowserStorage() : storage;
  const resolvedLockManager = lockManager === undefined ? resolveBrowserLockManager() : lockManager;

  const clearInvalidValue = (ownerId: string, key: string, invalidRaw: string): void => {
    if (!resolvedStorage || !resolvedLockManager) return;
    void resolvedLockManager
      .request(deckEditorDraftLockName(ownerId), { mode: 'exclusive' }, () => {
        try {
          if (resolvedStorage.getItem(key) === invalidRaw) resolvedStorage.removeItem(key);
        } catch {
          // Invalid-data cleanup is best effort; normal mutations report storage health.
        }
      })
      .catch(() => undefined);
  };

  const read = (ownerId: string): DeckEditorDraftReadResult => {
    if (!resolvedStorage || !resolvedLockManager || !ownerId) return { status: 'unavailable' };
    const key = deckEditorDraftStorageKey(ownerId);
    let raw: string | null;
    try {
      raw = resolvedStorage.getItem(key);
    } catch {
      return { status: 'unavailable' };
    }
    if (raw === null) return { status: 'loaded', slot: { kind: 'empty' } };
    let value: unknown;
    try {
      value = JSON.parse(raw) as unknown;
    } catch {
      clearInvalidValue(ownerId, key, raw);
      return { status: 'loaded', slot: { kind: 'empty' } };
    }
    const slot = parseDeckEditorDraftSlotValue(value, ownerId);
    if (slot === null) {
      clearInvalidValue(ownerId, key, raw);
      return { status: 'loaded', slot: { kind: 'empty' } };
    }
    return { status: 'loaded', slot };
  };

  const currentSlot = (ownerId: string): DeckEditorDraftReadResult => read(ownerId);

  const withOwnerLock = async <
    Result extends DeckEditorDraftSaveResult | DeckEditorDraftMutationResult,
  >(
    ownerId: string,
    operation: () => Result,
  ): Promise<Result | { status: 'unavailable' }> => {
    if (!resolvedStorage || !resolvedLockManager || !ownerId) return { status: 'unavailable' };
    try {
      return await resolvedLockManager.request(
        deckEditorDraftLockName(ownerId),
        { mode: 'exclusive' },
        operation,
      );
    } catch {
      return { status: 'unavailable' };
    }
  };

  return {
    read,
    async save(draft, expected) {
      return await withOwnerLock(draft.ownerId, () => {
        const current = currentSlot(draft.ownerId);
        if (current.status === 'unavailable') return current;
        if (!deckEditorDraftSlotTokensEqual(deckEditorDraftSlotToken(current.slot), expected)) {
          return { status: 'conflict' as const, slot: current.slot };
        }
        try {
          resolvedStorage?.setItem(deckEditorDraftStorageKey(draft.ownerId), JSON.stringify(draft));
        } catch {
          return { status: 'unavailable' as const };
        }
        return { status: 'saved' as const, draft };
      });
    },
    async discard(ownerId, expected) {
      return await withOwnerLock(ownerId, () => {
        const current = currentSlot(ownerId);
        if (current.status === 'unavailable') return current;
        if (!deckEditorDraftSlotTokensEqual(deckEditorDraftSlotToken(current.slot), expected)) {
          return { status: 'conflict' as const, slot: current.slot };
        }
        try {
          resolvedStorage?.removeItem(deckEditorDraftStorageKey(ownerId));
        } catch {
          return { status: 'unavailable' as const };
        }
        return { status: 'empty' as const };
      });
    },
    async retire(ownerId, draftId, createdDeckId, expected) {
      if (!createdDeckId) return { status: 'unavailable' };
      return await withOwnerLock(ownerId, () => {
        const current = currentSlot(ownerId);
        if (current.status === 'unavailable') return current;
        if (!deckEditorDraftSlotTokensEqual(deckEditorDraftSlotToken(current.slot), expected)) {
          return { status: 'conflict' as const, slot: current.slot };
        }
        const marker: RetiredDraft = {
          version: 2,
          kind: 'retired',
          ownerId,
          draftId,
          revision:
            current.slot.kind === 'draft' ? current.slot.draft.revision : crypto.randomUUID(),
          retiredAt: new Date().toISOString(),
          createdDeckId,
        };
        try {
          resolvedStorage?.setItem(deckEditorDraftStorageKey(ownerId), JSON.stringify(marker));
        } catch {
          return { status: 'unavailable' as const };
        }
        return { status: 'retired' as const, marker };
      });
    },
  };
};
