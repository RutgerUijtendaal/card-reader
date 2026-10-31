import {
  useLocalDraft,
  type LocalDraftOptions,
  type DraftConflict,
} from '@/shared/drafts/useLocalDraft';
import type { DeckCardSummary, DeckUpsertRequest } from '@/domain/decks/types';
import type { DeckForm } from './deckEditorDraftTypes';
import {
  buildStoredDeckEditorDraft,
  createDeckEditorLocalDraftStorage,
  deckEditorDraftStorageKey,
  parseDeckEditorDraftSlotValue,
} from '../utils/deckEditorLocalDraftStorage';
export type DeckEditorDraftConflict = DraftConflict<DeckForm, DeckCardSummary, DeckUpsertRequest>;
export const useDeckEditorLocalDraft = (
  options: Omit<
    LocalDraftOptions<DeckForm, DeckCardSummary, DeckUpsertRequest>,
    'key' | 'parse' | 'storage' | 'build'
  >,
) =>
  useLocalDraft({
    ...options,
    key: deckEditorDraftStorageKey,
    parse: parseDeckEditorDraftSlotValue,
    storage: createDeckEditorLocalDraftStorage(),
    build: buildStoredDeckEditorDraft,
  });
