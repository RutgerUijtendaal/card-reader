import type { DeckCardSummary } from '@/domain/decks/types';
import type {
  DeckForm,
  DeckFormEntry,
  DeckFormSideboard,
} from '@/features/decks/composables/deckEditorDraftTypes';

export const DECK_EDITOR_LOCAL_DRAFT_VERSION = 1;
const STORAGE_PREFIX = 'card-reader.deck-editor.new-draft.';

export type StoredDeckEditorDraft = {
  version: typeof DECK_EDITOR_LOCAL_DRAFT_VERSION;
  ownerId: string;
  savedAt: string;
  form: DeckForm;
  cards: Record<string, DeckCardSummary>;
};

type RetiredDeckEditorDraft = {
  version: typeof DECK_EDITOR_LOCAL_DRAFT_VERSION;
  ownerId: string;
  retiredAt: string;
  createdDeckId: string;
};

export type DeckEditorLocalDraftStorage = {
  load: (ownerId: string) => StoredDeckEditorDraft | null;
  save: (
    ownerId: string,
    form: DeckForm,
    cardLookup: Record<string, DeckCardSummary>,
  ) => StoredDeckEditorDraft;
  clear: (ownerId: string) => void;
  retire: (ownerId: string, createdDeckId: string) => void;
};

const storageKey = (ownerId: string): string => `${STORAGE_PREFIX}${ownerId}`;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === 'string');

const isRetiredDraft = (value: unknown, ownerId: string): value is RetiredDeckEditorDraft =>
  isRecord(value)
  && value.version === DECK_EDITOR_LOCAL_DRAFT_VERSION
  && value.ownerId === ownerId
  && typeof value.retiredAt === 'string'
  && typeof value.createdDeckId === 'string';

const normalizeEntry = (value: unknown): DeckFormEntry | null => {
  if (!isRecord(value) || typeof value.card_id !== 'string') {
    return null;
  }
  if (!Number.isInteger(value.quantity) || Number(value.quantity) < 1) {
    return null;
  }
  return {
    card_id: value.card_id,
    quantity: Number(value.quantity),
  };
};

const normalizeEntries = (value: unknown): DeckFormEntry[] | null => {
  if (!Array.isArray(value)) {
    return null;
  }
  const entries = value.map(normalizeEntry);
  return entries.every((entry): entry is DeckFormEntry => entry !== null) ? entries : null;
};

const normalizeSideboard = (value: unknown): DeckFormSideboard | null => {
  if (!isRecord(value) || typeof value.id !== 'string' || typeof value.name !== 'string') {
    return null;
  }
  const entries = normalizeEntries(value.entries);
  return entries === null ? null : { id: value.id, name: value.name, entries };
};

const normalizeForm = (value: unknown): DeckForm | null => {
  if (!isRecord(value)) {
    return null;
  }
  const entries = normalizeEntries(value.entries);
  if (entries === null || !Array.isArray(value.sideboards)) {
    return null;
  }
  const sideboards = value.sideboards.map(normalizeSideboard);
  if (!sideboards.every((sideboard): sideboard is DeckFormSideboard => sideboard !== null)) {
    return null;
  }
  if (
    typeof value.name !== 'string'
    || typeof value.description !== 'string'
    || typeof value.long_description !== 'string'
    || (value.difficulty !== null
      && value.difficulty !== 'easy'
      && value.difficulty !== 'medium'
      && value.difficulty !== 'hard')
    || (value.visibility !== 'private'
      && value.visibility !== 'unlisted'
      && value.visibility !== 'public')
    || typeof value.hero_card_id !== 'string'
    || !isStringArray(value.tag_ids)
    || !isStringArray(value.suggested_type_labels)
  ) {
    return null;
  }
  return {
    name: value.name,
    description: value.description,
    long_description: value.long_description,
    difficulty: value.difficulty,
    visibility: value.visibility,
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

const isCardSnapshot = (value: unknown): value is DeckCardSummary => {
  if (!isRecord(value)) {
    return false;
  }
  return (
    value.result_type === 'card'
    && typeof value.id === 'string'
    && typeof value.key === 'string'
    && typeof value.label === 'string'
    && typeof value.is_hero === 'boolean'
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
    && Array.isArray(value.tags)
    && value.tags.every(isMetadataOption)
    && Array.isArray(value.symbols)
    && value.symbols.every(isSymbolOption)
    && Array.isArray(value.types)
    && value.types.every(isMetadataOption)
    && (value.image_url === null || typeof value.image_url === 'string')
  );
};

const normalizeCards = (value: unknown): Record<string, DeckCardSummary> | null => {
  if (!isRecord(value)) {
    return null;
  }
  const cards: Record<string, DeckCardSummary> = {};
  for (const card of Object.values(value)) {
    if (!isCardSnapshot(card)) {
      return null;
    }
    cards[card.id] = card;
  }
  return cards;
};

export const parseStoredDeckEditorDraft = (
  value: unknown,
  ownerId: string,
): StoredDeckEditorDraft | null => {
  if (
    !isRecord(value)
    || value.version !== DECK_EDITOR_LOCAL_DRAFT_VERSION
    || value.ownerId !== ownerId
    || typeof value.savedAt !== 'string'
  ) {
    return null;
  }
  const form = normalizeForm(value.form);
  const cards = normalizeCards(value.cards);
  if (form === null || cards === null) {
    return null;
  }
  return {
    version: DECK_EDITOR_LOCAL_DRAFT_VERSION,
    ownerId,
    savedAt: value.savedAt,
    form,
    cards,
  };
};

const referencedCardIds = (form: DeckForm): Set<string> => {
  const ids = new Set<string>();
  if (form.hero_card_id) {
    ids.add(form.hero_card_id);
  }
  for (const entry of form.entries) {
    ids.add(entry.card_id);
  }
  for (const sideboard of form.sideboards) {
    for (const entry of sideboard.entries) {
      ids.add(entry.card_id);
    }
  }
  return ids;
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

export const buildStoredDeckEditorDraft = (
  ownerId: string,
  form: DeckForm,
  cardLookup: Record<string, DeckCardSummary>,
): StoredDeckEditorDraft => {
  const cards: Record<string, DeckCardSummary> = {};
  for (const cardId of referencedCardIds(form)) {
    const card = cardLookup[cardId];
    if (card) {
      cards[cardId] = card;
    }
  }
  return {
    version: DECK_EDITOR_LOCAL_DRAFT_VERSION,
    ownerId,
    savedAt: new Date().toISOString(),
    form: cloneForm(form),
    cards,
  };
};

const resolveBrowserStorage = (): Storage | null => {
  try {
    return typeof globalThis.localStorage === 'undefined' ? null : globalThis.localStorage;
  } catch {
    return null;
  }
};

export const createDeckEditorLocalDraftStorage = (
  storage?: Storage | null,
): DeckEditorLocalDraftStorage => {
  const resolvedStorage = storage === undefined ? resolveBrowserStorage() : storage;
  const requireStorage = (): Storage => {
    if (!resolvedStorage) {
      throw new Error('Local draft storage is unavailable.');
    }
    return resolvedStorage;
  };

  return {
    load(ownerId) {
      if (!ownerId) {
        return null;
      }
      const activeStorage = requireStorage();
      const key = storageKey(ownerId);
      let raw: string | null;
      try {
        raw = activeStorage.getItem(key);
      } catch {
        throw new Error('Local draft storage is unavailable.');
      }
      if (!raw) {
        return null;
      }
      let storedValue: unknown;
      try {
        storedValue = JSON.parse(raw) as unknown;
      } catch {
        try {
          activeStorage.removeItem(key);
        } catch {
          throw new Error('Local draft storage is unavailable.');
        }
        return null;
      }
      if (isRetiredDraft(storedValue, ownerId)) {
        try {
          activeStorage.removeItem(key);
        } catch {
          // A retirement marker is safe to leave behind because it is never recoverable as a draft.
        }
        return null;
      }
      const parsed = parseStoredDeckEditorDraft(storedValue, ownerId);
      if (parsed === null) {
        activeStorage.removeItem(key);
      }
      return parsed;
    },
    save(ownerId, form, cardLookup) {
      if (!ownerId) {
        throw new Error('Local draft storage is unavailable.');
      }
      const activeStorage = requireStorage();
      const draft = buildStoredDeckEditorDraft(ownerId, form, cardLookup);
      activeStorage.setItem(storageKey(ownerId), JSON.stringify(draft));
      return draft;
    },
    clear(ownerId) {
      if (!ownerId) {
        return;
      }
      requireStorage().removeItem(storageKey(ownerId));
    },
    retire(ownerId, createdDeckId) {
      if (!ownerId || !createdDeckId) {
        throw new Error('Local draft storage is unavailable.');
      }
      const activeStorage = requireStorage();
      const key = storageKey(ownerId);
      try {
        activeStorage.removeItem(key);
      } catch {
        const marker: RetiredDeckEditorDraft = {
          version: DECK_EDITOR_LOCAL_DRAFT_VERSION,
          ownerId,
          retiredAt: new Date().toISOString(),
          createdDeckId,
        };
        activeStorage.setItem(key, JSON.stringify(marker));
      }
    },
  };
};
