import type { DeckCardSummary, DeckUpsertRequest } from '@/domain/decks/types';
import type {
  DeckForm,
  DeckFormEntry,
  DeckFormSideboard,
} from '@/features/decks/composables/deckEditorDraftTypes';

export const DECK_EDITOR_LOCAL_DRAFT_VERSION = 2;
const LEGACY_DECK_EDITOR_LOCAL_DRAFT_VERSION = 1;
export const DECK_EDITOR_LOCAL_DRAFT_STORAGE_PREFIX = 'card-reader.deck-editor.new-draft.';

export type StoredCreateAttempt = {
  payload: DeckUpsertRequest;
  signature: string;
  startedAt: string;
};

export type StoredDeckEditorDraft = {
  version: typeof DECK_EDITOR_LOCAL_DRAFT_VERSION;
  kind: 'draft';
  ownerId: string;
  draftId: string;
  revision: string;
  savedAt: string;
  form: DeckForm;
  cards: Record<string, DeckCardSummary>;
  pendingCreateAttempt: StoredCreateAttempt | null;
};

export type RetiredDeckEditorDraft = {
  version: typeof DECK_EDITOR_LOCAL_DRAFT_VERSION;
  kind: 'retired';
  ownerId: string;
  draftId: string;
  revision: string;
  retiredAt: string;
  createdDeckId: string;
};

export type DeckEditorDraftSlot =
  | { kind: 'empty' }
  | { kind: 'draft'; draft: StoredDeckEditorDraft }
  | { kind: 'retired'; marker: RetiredDeckEditorDraft };

export type DeckEditorDraftSlotToken =
  | { kind: 'empty' }
  | { kind: 'draft'; revision: string }
  | { kind: 'retired'; revision: string };

export type DeckEditorDraftReadResult =
  | { status: 'loaded'; slot: DeckEditorDraftSlot }
  | { status: 'unavailable' };

export type DeckEditorDraftSaveResult =
  | { status: 'saved'; draft: StoredDeckEditorDraft }
  | { status: 'conflict'; slot: DeckEditorDraftSlot }
  | { status: 'unavailable' };

export type DeckEditorDraftMutationResult =
  | { status: 'empty' }
  | { status: 'retired'; marker: RetiredDeckEditorDraft }
  | { status: 'conflict'; slot: DeckEditorDraftSlot }
  | { status: 'unavailable' };

export type DeckEditorLocalDraftStorage = {
  read: (ownerId: string) => DeckEditorDraftReadResult;
  save: (
    draft: StoredDeckEditorDraft,
    expected: DeckEditorDraftSlotToken,
  ) => Promise<DeckEditorDraftSaveResult>;
  discard: (
    ownerId: string,
    expected: DeckEditorDraftSlotToken,
  ) => Promise<DeckEditorDraftMutationResult>;
  retire: (
    ownerId: string,
    draftId: string,
    createdDeckId: string,
    expected: DeckEditorDraftSlotToken,
  ) => Promise<DeckEditorDraftMutationResult>;
};

export type DeckEditorDraftLockManager = {
  request: <Result>(
    name: string,
    options: { mode: 'exclusive' },
    callback: () => Result | PromiseLike<Result>,
  ) => Promise<Result>;
};

export const deckEditorDraftStorageKey = (ownerId: string): string =>
  `${DECK_EDITOR_LOCAL_DRAFT_STORAGE_PREFIX}${ownerId}`;

const createUuid = (): string => {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16);
    const value = character === 'x' ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
};

export const createDeckEditorDraftId = (): string => createUuid();

const isRecord = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === 'string');

const normalizeEntry = (value: unknown): DeckFormEntry | null => {
  if (!isRecord(value) || typeof value.card_id !== 'string') return null;
  if (!Number.isInteger(value.quantity) || Number(value.quantity) < 1) return null;
  return { card_id: value.card_id, quantity: Number(value.quantity) };
};

const normalizeEntries = (value: unknown): DeckFormEntry[] | null => {
  if (!Array.isArray(value)) return null;
  const entries = value.map(normalizeEntry);
  return entries.every((entry): entry is DeckFormEntry => entry !== null) ? entries : null;
};

const normalizeSideboard = (value: unknown): DeckFormSideboard | null => {
  if (!isRecord(value) || typeof value.id !== 'string' || typeof value.name !== 'string') return null;
  if (value.source_id !== undefined && typeof value.source_id !== 'string') return null;
  const entries = normalizeEntries(value.entries);
  return entries === null
    ? null
    : {
        id: value.id,
        ...(value.source_id ? { source_id: value.source_id } : {}),
        name: value.name,
        entries,
      };
};

const normalizeForm = (value: unknown): DeckForm | null => {
  if (!isRecord(value)) return null;
  const entries = normalizeEntries(value.entries);
  if (entries === null || !Array.isArray(value.sideboards)) return null;
  const sideboards = value.sideboards.map(normalizeSideboard);
  if (!sideboards.every((sideboard): sideboard is DeckFormSideboard => sideboard !== null)) return null;
  if (
    typeof value.name !== 'string'
    || typeof value.description !== 'string'
    || typeof value.long_description !== 'string'
    || (value.difficulty !== null && !['easy', 'medium', 'hard'].includes(String(value.difficulty)))
    || !['private', 'unlisted', 'public'].includes(String(value.visibility))
    || typeof value.hero_card_id !== 'string'
    || !isStringArray(value.tag_ids)
    || !isStringArray(value.suggested_type_labels)
  ) return null;
  return {
    name: value.name,
    description: value.description,
    long_description: value.long_description,
    difficulty: value.difficulty as DeckForm['difficulty'],
    visibility: value.visibility as DeckForm['visibility'],
    hero_card_id: value.hero_card_id,
    entries,
    sideboards,
    tag_ids: [...value.tag_ids],
    suggested_type_labels: [...value.suggested_type_labels],
  };
};

const isMetadataOption = (value: unknown): boolean =>
  isRecord(value)
  && typeof value.id === 'string'
  && typeof value.key === 'string'
  && typeof value.label === 'string';

const isSymbolOption = (value: unknown): boolean =>
  isMetadataOption(value)
  && isRecord(value)
  && typeof value.symbol_type === 'string'
  && typeof value.text_token === 'string'
  && (value.asset_url === null || typeof value.asset_url === 'string');

const normalizeCardSnapshot = (value: unknown): DeckCardSummary | null => {
  if (!isRecord(value)) return null;
  let cardPool: DeckCardSummary['card_pool'];
  let cardRoles: DeckCardSummary['card_roles'];
  if (
    (value.card_pool === 'player' || value.card_pool === 'evil' || value.card_pool === 'neutral')
    && isStringArray(value.card_roles)
  ) {
    cardPool = value.card_pool;
    cardRoles = [...value.card_roles] as DeckCardSummary['card_roles'];
  } else if (typeof value.is_hero === 'boolean') {
    cardPool = 'player';
    cardRoles = value.is_hero ? ['hero'] : [];
  } else {
    return null;
  }
  if (!(value.result_type === 'card'
  && typeof value.id === 'string'
  && typeof value.key === 'string'
  && typeof value.label === 'string'
  && typeof value.template_id === 'string'
  && typeof value.version_id === 'string'
  && typeof value.version_number === 'number'
  && (value.previous_version_id === null || typeof value.previous_version_id === 'string')
  && typeof value.is_latest === 'boolean'
  && typeof value.name === 'string'
  && typeof value.type_line === 'string'
  && typeof value.mana_cost === 'string'
  && isStringArray(value.mana_symbols)
  && (value.mana_value === null || typeof value.mana_value === 'number')
  && (value.attack === null || typeof value.attack === 'number')
  && (value.health === null || typeof value.health === 'number')
  && typeof value.rules_text === 'string'
  && typeof value.confidence === 'number'
  && typeof value.created_at === 'string'
  && typeof value.updated_at === 'string'
  && isStringArray(value.keywords)
  && Array.isArray(value.tags) && value.tags.every(isMetadataOption)
  && Array.isArray(value.symbols) && value.symbols.every(isSymbolOption)
  && Array.isArray(value.types) && value.types.every(isMetadataOption)
  && (value.image_url === null || typeof value.image_url === 'string'))) return null;

  const normalized: Record<string, unknown> = {
    ...value,
    card_pool: cardPool,
    card_roles: cardRoles,
  };
  delete normalized.is_hero;
  return normalized as DeckCardSummary;
};

const normalizeCards = (value: unknown): Record<string, DeckCardSummary> | null => {
  if (!isRecord(value)) return null;
  const cards: Record<string, DeckCardSummary> = {};
  for (const card of Object.values(value)) {
    const normalized = normalizeCardSnapshot(card);
    if (normalized === null) return null;
    cards[normalized.id] = normalized;
  }
  return cards;
};

const normalizePayload = (value: unknown): DeckUpsertRequest | null => {
  if (!isRecord(value)) return null;
  const entries = normalizeEntries(value.entries);
  if (entries === null || !Array.isArray(value.sideboards)) return null;
  const sideboards = value.sideboards.map((sideboard) => {
    if (!isRecord(sideboard) || typeof sideboard.name !== 'string') return null;
    const sideboardEntries = normalizeEntries(sideboard.entries);
    return sideboardEntries === null ? null : { name: sideboard.name, entries: sideboardEntries };
  });
  if (
    !sideboards.every((sideboard): sideboard is DeckUpsertRequest['sideboards'][number] => sideboard !== null)
    || typeof value.name !== 'string'
    || (value.description !== null && typeof value.description !== 'string')
    || (value.long_description !== null && typeof value.long_description !== 'string')
    || (value.difficulty !== null && !['easy', 'medium', 'hard'].includes(String(value.difficulty)))
    || !['private', 'unlisted', 'public'].includes(String(value.visibility))
    || typeof value.hero_card_id !== 'string'
    || !isStringArray(value.tag_ids)
    || !isStringArray(value.suggested_type_labels)
  ) return null;
  return {
    name: value.name,
    description: value.description,
    long_description: value.long_description,
    difficulty: value.difficulty as DeckUpsertRequest['difficulty'],
    visibility: value.visibility as DeckUpsertRequest['visibility'],
    hero_card_id: value.hero_card_id,
    entries,
    sideboards,
    tag_ids: [...value.tag_ids],
    suggested_type_labels: [...value.suggested_type_labels],
  };
};

const normalizeAttempt = (value: unknown): StoredCreateAttempt | null => {
  if (value === null) return null;
  if (!isRecord(value) || typeof value.signature !== 'string' || typeof value.startedAt !== 'string') return null;
  const payload = normalizePayload(value.payload);
  return payload === null ? null : { payload, signature: value.signature, startedAt: value.startedAt };
};

const cloneForm = (form: DeckForm): DeckForm => ({
  ...form,
  entries: form.entries.map((entry) => ({ ...entry })),
  sideboards: form.sideboards.map((sideboard) => ({
    ...sideboard,
    entries: sideboard.entries.map((entry) => ({ ...entry })),
  })),
  tag_ids: [...form.tag_ids],
  suggested_type_labels: [...form.suggested_type_labels],
});

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

const referencedCardIds = (form: DeckForm): Set<string> => new Set([
  ...(form.hero_card_id ? [form.hero_card_id] : []),
  ...form.entries.map((entry) => entry.card_id),
  ...form.sideboards.flatMap((sideboard) => sideboard.entries.map((entry) => entry.card_id)),
]);

export const buildStoredDeckEditorDraft = (
  ownerId: string,
  draftId: string,
  form: DeckForm,
  cardLookup: Record<string, DeckCardSummary>,
  pendingCreateAttempt: StoredCreateAttempt | null = null,
): StoredDeckEditorDraft => {
  const cards: Record<string, DeckCardSummary> = {};
  for (const cardId of referencedCardIds(form)) {
    const card = cardLookup[cardId];
    if (card) cards[cardId] = card;
  }
  return {
    version: DECK_EDITOR_LOCAL_DRAFT_VERSION,
    kind: 'draft',
    ownerId,
    draftId,
    revision: createUuid(),
    savedAt: new Date().toISOString(),
    form: cloneForm(form),
    cards,
    pendingCreateAttempt: pendingCreateAttempt
      ? { ...pendingCreateAttempt, payload: clonePayload(pendingCreateAttempt.payload) }
      : null,
  };
};

const parseV2Draft = (value: unknown, ownerId: string): StoredDeckEditorDraft | null => {
  if (
    !isRecord(value)
    || value.version !== DECK_EDITOR_LOCAL_DRAFT_VERSION
    || value.kind !== 'draft'
    || value.ownerId !== ownerId
    || typeof value.draftId !== 'string'
    || typeof value.revision !== 'string'
    || typeof value.savedAt !== 'string'
  ) return null;
  const form = normalizeForm(value.form);
  const cards = normalizeCards(value.cards);
  const attempt = normalizeAttempt(value.pendingCreateAttempt);
  if (form === null || cards === null || (value.pendingCreateAttempt !== null && attempt === null)) return null;
  return {
    version: 2,
    kind: 'draft',
    ownerId,
    draftId: value.draftId,
    revision: value.revision,
    savedAt: value.savedAt,
    form,
    cards,
    pendingCreateAttempt: attempt,
  };
};

const parseRetired = (value: unknown, ownerId: string): RetiredDeckEditorDraft | null => {
  if (
    !isRecord(value)
    || value.version !== DECK_EDITOR_LOCAL_DRAFT_VERSION
    || value.kind !== 'retired'
    || value.ownerId !== ownerId
    || typeof value.draftId !== 'string'
    || typeof value.revision !== 'string'
    || typeof value.retiredAt !== 'string'
    || typeof value.createdDeckId !== 'string'
  ) return null;
  return value as RetiredDeckEditorDraft;
};

const migrateV1Draft = (value: unknown, ownerId: string): StoredDeckEditorDraft | null => {
  if (
    !isRecord(value)
    || value.version !== LEGACY_DECK_EDITOR_LOCAL_DRAFT_VERSION
    || value.ownerId !== ownerId
    || typeof value.savedAt !== 'string'
  ) return null;
  const form = normalizeForm(value.form);
  const cards = normalizeCards(value.cards);
  if (form === null || cards === null) return null;
  return {
    version: 2,
    kind: 'draft',
    ownerId,
    draftId: createUuid(),
    revision: `v1:${value.savedAt}`,
    savedAt: value.savedAt,
    form,
    cards,
    pendingCreateAttempt: null,
  };
};

export const parseDeckEditorDraftSlotValue = (
  value: unknown,
  ownerId: string,
): DeckEditorDraftSlot | null => {
  const draft = parseV2Draft(value, ownerId) ?? migrateV1Draft(value, ownerId);
  if (draft) return { kind: 'draft', draft };
  const marker = parseRetired(value, ownerId);
  return marker ? { kind: 'retired', marker } : null;
};

export const deckEditorDraftSlotToken = (slot: DeckEditorDraftSlot): DeckEditorDraftSlotToken => {
  if (slot.kind === 'draft') return { kind: 'draft', revision: slot.draft.revision };
  if (slot.kind === 'retired') return { kind: 'retired', revision: slot.marker.revision };
  return { kind: 'empty' };
};

export const deckEditorDraftSlotTokensEqual = (
  left: DeckEditorDraftSlotToken,
  right: DeckEditorDraftSlotToken,
): boolean => left.kind === right.kind
  && (left.kind === 'empty' || (right.kind !== 'empty' && left.revision === right.revision));

const resolveBrowserStorage = (): Storage | null => {
  try {
    return typeof globalThis.localStorage === 'undefined' ? null : globalThis.localStorage;
  } catch {
    return null;
  }
};

const resolveBrowserLockManager = (): DeckEditorDraftLockManager | null => {
  try {
    if (typeof globalThis.navigator === 'undefined' || !globalThis.navigator.locks) return null;
    return globalThis.navigator.locks;
  } catch {
    return null;
  }
};

const deckEditorDraftLockName = (ownerId: string): string =>
  `${deckEditorDraftStorageKey(ownerId)}.mutation`;

export const createDeckEditorLocalDraftStorage = (
  storage?: Storage | null,
  lockManager?: DeckEditorDraftLockManager | null,
): DeckEditorLocalDraftStorage => {
  const resolvedStorage = storage === undefined ? resolveBrowserStorage() : storage;
  const resolvedLockManager = lockManager === undefined ? resolveBrowserLockManager() : lockManager;

  const clearInvalidValue = (ownerId: string, key: string, invalidRaw: string): void => {
    if (!resolvedStorage || !resolvedLockManager) return;
    void resolvedLockManager.request(
      deckEditorDraftLockName(ownerId),
      { mode: 'exclusive' },
      () => {
        try {
          if (resolvedStorage.getItem(key) === invalidRaw) resolvedStorage.removeItem(key);
        } catch {
          // Invalid-data cleanup is best effort; normal mutations report storage health.
        }
      },
    ).catch(() => undefined);
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

  const withOwnerLock = async <Result extends DeckEditorDraftSaveResult | DeckEditorDraftMutationResult>(
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
        const marker: RetiredDeckEditorDraft = {
          version: 2,
          kind: 'retired',
          ownerId,
          draftId,
          revision: current.slot.kind === 'draft' ? current.slot.draft.revision : createUuid(),
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
