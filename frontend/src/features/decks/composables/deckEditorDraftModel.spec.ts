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
        source_id: 'sideboard-1',
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

  test('does not send temporary editor ids for new sideboards', () => {
    const form = createEmptyDeckForm();
    form.sideboards = [
      {
        id: 'sideboard-local-1',
        name: ' New sideboard ',
        entries: [],
      },
    ];

    expect(buildDeckUpsertPayload(form).sideboards).toEqual([
      {
        name: 'New sideboard',
        entries: [],
      },
    ]);
  });
});
