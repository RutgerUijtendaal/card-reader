import type { DeckCardSummary, DeckRecord, DeckUpsertRequest } from '@/domain/decks/types';
import type {
  DeckForm,
  DeckFormEntry,
} from '@/features/decks/composables/deckEditorDraftTypes';

export type DeckSideboardSubmissionSnapshot = {
  editorId: string;
  sourceId?: string;
  name: string;
  entries: DeckFormEntry[];
};

export const createEmptyDeckForm = (): DeckForm => ({
  name: '',
  description: '',
  long_description: '',
  difficulty: null,
  visibility: 'private',
  hero_card_id: '',
  entries: [],
  sideboards: [],
  tag_ids: [],
  suggested_type_labels: [],
});

export const hydrateDeckForm = (form: DeckForm, deck: DeckRecord): void => {
  form.name = deck.name;
  form.description = deck.description ?? '';
  form.long_description = deck.long_description ?? '';
  form.difficulty = deck.difficulty;
  form.visibility = deck.visibility;
  form.hero_card_id = deck.hero_card.id;
  form.tag_ids = (deck.tags ?? []).map((tag) => tag.id);
  form.suggested_type_labels = (deck.pending_tag_suggestions ?? []).map(
    (suggestion) => suggestion.label,
  );
  form.entries = deck.mainboard.entries.map((entry) => ({
    card_id: entry.card.id,
    quantity: entry.quantity,
  }));
  form.sideboards = deck.sideboards.map((sideboard) => ({
    id: sideboard.id,
    source_id: sideboard.id,
    name: sideboard.name,
    entries: sideboard.entries.map((entry) => ({
      card_id: entry.card.id,
      quantity: entry.quantity,
    })),
  }));
};

export const buildDeckCardLookup = (
  currentLookup: Record<string, DeckCardSummary>,
  deck: DeckRecord,
): Record<string, DeckCardSummary> => {
  const nextLookup = { ...currentLookup, [deck.hero_card.id]: deck.hero_card };
  for (const entry of deck.mainboard.entries) nextLookup[entry.card.id] = entry.card;
  for (const sideboard of deck.sideboards) {
    for (const entry of sideboard.entries) nextLookup[entry.card.id] = entry.card;
  }
  return nextLookup;
};

export const buildDeckUpsertPayload = (form: DeckForm): DeckUpsertRequest => ({
  name: form.name.trim(),
  description: form.description.trim() || null,
  long_description: form.long_description.trim() || null,
  difficulty: form.difficulty,
  visibility: form.visibility,
  hero_card_id: form.hero_card_id,
  entries: form.entries.map((entry) => ({ ...entry })),
  sideboards: form.sideboards.map((sideboard) => ({
    ...(sideboard.source_id ? { id: sideboard.source_id } : {}),
    name: sideboard.name.trim(),
    entries: sideboard.entries.map((entry) => ({ ...entry })),
  })),
  tag_ids: [...form.tag_ids],
  suggested_type_labels: [...form.suggested_type_labels],
});

export const reconcilePersistedSideboardSourceIds = (
  form: DeckForm,
  submittedSideboards: readonly DeckSideboardSubmissionSnapshot[],
  deck: {
    sideboards?: ReadonlyArray<{
      id: string;
      name: string;
      entries: ReadonlyArray<{ card: { id: string }; quantity: number }>;
    }>;
  },
): void => {
  const persistedSideboards = deck.sideboards ?? [];
  const persistedById = new Map(
    persistedSideboards.map((sideboard) => [sideboard.id, sideboard]),
  );
  const usedPersistedIds = new Set<string>();
  const assignSourceId = (
    submittedSideboard: DeckSideboardSubmissionSnapshot,
    persistedId: string,
  ): void => {
    const currentSideboard = form.sideboards.find(
      (sideboard) => sideboard.id === submittedSideboard.editorId,
    );
    if (currentSideboard) {
      currentSideboard.source_id = persistedId;
      usedPersistedIds.add(persistedId);
    }
  };

  for (const submittedSideboard of submittedSideboards) {
    const persistedSideboard = submittedSideboard.sourceId
      ? persistedById.get(submittedSideboard.sourceId)
      : undefined;
    if (persistedSideboard && !usedPersistedIds.has(persistedSideboard.id)) {
      assignSourceId(submittedSideboard, persistedSideboard.id);
    }
  }

  for (const submittedSideboard of submittedSideboards) {
    const currentSideboard = form.sideboards.find(
      (sideboard) => sideboard.id === submittedSideboard.editorId,
    );
    if (!currentSideboard || usedPersistedIds.has(currentSideboard.source_id ?? '')) {
      continue;
    }
    const submittedEntries = sideboardEntrySignature(submittedSideboard.entries);
    const persistedSideboard = persistedSideboards.find(
      (candidate) => !usedPersistedIds.has(candidate.id)
        && candidate.name === submittedSideboard.name
        && sideboardEntrySignature(
          candidate.entries.map((entry) => ({
            card_id: entry.card.id,
            quantity: entry.quantity,
          })),
        ) === submittedEntries,
    );
    if (persistedSideboard) {
      assignSourceId(submittedSideboard, persistedSideboard.id);
    }
  }
};

export const snapshotSubmittedSideboards = (
  form: DeckForm,
): DeckSideboardSubmissionSnapshot[] => form.sideboards.map((sideboard) => ({
  editorId: sideboard.id,
  ...(sideboard.source_id ? { sourceId: sideboard.source_id } : {}),
  name: sideboard.name.trim(),
  entries: sideboard.entries.map((entry) => ({ ...entry })),
}));

const sideboardEntrySignature = (entries: readonly DeckFormEntry[]): string => JSON.stringify(entries);
