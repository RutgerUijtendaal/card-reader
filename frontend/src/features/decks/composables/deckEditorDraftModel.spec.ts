import { describe, expect, test } from 'vitest';

import {
  buildDeckUpsertPayload,
  createEmptyDeckForm,
  reconcilePersistedSideboardSourceIds,
  snapshotSubmittedSideboards,
} from '@/features/decks/composables/deckEditorDraftModel';

describe('deckEditorDraftModel', () => {
  test('preserves Markdown-significant whitespace in submission payloads', () => {
    const form = createEmptyDeckForm();
    form.description = '    [[card:id|Literal]]\n';
    form.long_description = 'Line with a hard break  \nNext';

    expect(buildDeckUpsertPayload(form)).toMatchObject({
      description_markup: '    [[card:id|Literal]]\n',
      long_description_markup: 'Line with a hard break  \nNext',
    });
  });
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

  test('matches persisted source ids by identity and content instead of response order', () => {
    const form = createEmptyDeckForm();
    form.sideboards = [
      { id: 'local-a', source_id: 'stale-a', name: 'A', entries: [] },
      { id: 'local-b', source_id: 'stale-b', name: 'B', entries: [] },
    ];
    const submittedSideboards = snapshotSubmittedSideboards(form);
    const deck = {
      sideboards: [
        { id: 'fresh-b', name: 'B', entries: [] },
        { id: 'fresh-a', name: 'A', entries: [] },
      ],
    };

    reconcilePersistedSideboardSourceIds(form, submittedSideboards, deck);

    expect(form.sideboards).toEqual([
      { id: 'local-a', source_id: 'fresh-a', name: 'A', entries: [] },
      { id: 'local-b', source_id: 'fresh-b', name: 'B', entries: [] },
    ]);
  });

  test('matches persisted source ids after canonical sideboard name normalization', () => {
    const form = createEmptyDeckForm();
    form.sideboards = [
      {
        id: 'local-sideboard',
        name: '  Side  \t Board  ',
        entries: [{ card_id: 'card-1', quantity: 1 }],
      },
    ];
    const submittedSideboards = snapshotSubmittedSideboards(form);
    const deck = {
      sideboards: [
        {
          id: 'persisted-sideboard',
          name: 'Side Board',
          entries: [{ card: { id: 'card-1' }, quantity: 1 }],
        },
      ],
    };

    reconcilePersistedSideboardSourceIds(form, submittedSideboards, deck);

    expect(buildDeckUpsertPayload(form).sideboards).toEqual([
      {
        id: 'persisted-sideboard',
        name: 'Side Board',
        entries: [{ card_id: 'card-1', quantity: 1 }],
      },
    ]);
  });
});
