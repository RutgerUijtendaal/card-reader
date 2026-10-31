import { useDraftCreation, type DraftCreationOptions } from '@/shared/drafts/useDraftCreation';
import { createDeck, fetchMyDeckByCreationKey } from '@/domain/decks/api';
import type { DeckRecord, DeckUpsertRequest } from '@/domain/decks/types';
export const useDeckEditorPublication = (
  options: Omit<
    DraftCreationOptions<DeckUpsertRequest, DeckRecord>,
    'createRequest' | 'lookupRequest'
  >,
) =>
  useDraftCreation({
    ...options,
    createRequest: createDeck,
    lookupRequest: fetchMyDeckByCreationKey,
  });
