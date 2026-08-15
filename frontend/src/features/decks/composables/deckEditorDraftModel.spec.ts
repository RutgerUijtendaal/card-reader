import { describe, expect, test } from 'vitest';

import {
  buildDeckUpsertPayload,
  createEmptyDeckForm,
  reconcilePersistedSideboardSourceIds,
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

  test('refreshes persisted source ids without replacing editor identities', () => {
    const form = createEmptyDeckForm();
    form.sideboards = [
      { id: 'local-a', source_id: 'stale-a', name: 'A', entries: [] },
      { id: 'local-b', source_id: 'stale-b', name: 'B', entries: [] },
    ];
    const deck = {
      sideboards: [
        { id: 'fresh-a' },
        { id: 'fresh-b' },
      ],
    };

    reconcilePersistedSideboardSourceIds(form, ['local-a', 'local-b'], deck);

    expect(form.sideboards).toEqual([
      { id: 'local-a', source_id: 'fresh-a', name: 'A', entries: [] },
      { id: 'local-b', source_id: 'fresh-b', name: 'B', entries: [] },
    ]);
  });
});
