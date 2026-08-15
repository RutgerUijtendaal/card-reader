import { describe, expect, test } from 'vitest';

import {
  buildDeckUpsertPayload,
  createEmptyDeckForm,
} from '@/features/decks/composables/deckEditorDraftModel';

describe('deckEditorDraftModel', () => {
  test('preserves source sideboard ids in update payloads', () => {
    const form = createEmptyDeckForm();
    form.sideboards = [
      {
        id: 'sideboard-1',
        name: ' Renamed sideboard ',
        entries: [{ card_id: 'card-1', quantity: 2 }],
      },
    ];

    expect(buildDeckUpsertPayload(form).sideboards).toEqual([
      {
        id: 'sideboard-1',
        name: 'Renamed sideboard',
        entries: [{ card_id: 'card-1', quantity: 2 }],
      },
    ]);
  });
});
