import { describe, expect, test, beforeEach } from 'vitest';
import { createLocalPlaytestStorage } from '@/modules/playtester/localPlaytestStorage';

describe('localPlaytestStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('migrates version 1 drafts by adding visual pile and opening setup fields', () => {
    const storage = createLocalPlaytestStorage();
    localStorage.setItem('card-reader.playtester.deck-1', JSON.stringify({
      version: 1,
      deckId: 'deck-1',
      deckUpdatedAt: '2026-01-01T00:00:00Z',
      savedAt: '2026-01-01T00:00:00Z',
      state: {
        deckId: 'deck-1',
        deckUpdatedAt: '2026-01-01T00:00:00Z',
        phase: 'setup',
        handSize: 7,
        stackFaces: { library: 'back' },
        setupSnapshot: {
          instances: [
            {
              instanceId: 'card-1:main:1',
              cardId: 'card-1',
              card: {},
              zoneId: 'library',
              order: 0,
              tapped: false,
              setupOrigin: false,
              boardX: null,
              boardY: null,
            },
          ],
        },
        instances: [
          {
            instanceId: 'card-1:main:1',
            cardId: 'card-1',
            card: {},
            zoneId: 'library',
            order: 0,
            tapped: false,
            setupOrigin: false,
            boardX: null,
            boardY: null,
          },
        ],
      },
    }));

    const draft = storage.load('deck-1');

    expect(draft?.version).toBe(3);
    expect(draft?.state.phase).toBe('opening');
    expect(draft?.state.openingSetup).toEqual({
      selectedManaInstanceIds: [],
      selectedSetupInstanceIds: [],
    });
    expect(draft?.state.instances[0]?.pileGroupId).toBeNull();
    expect(draft?.state.instances[0]?.pileOrder).toBeNull();
    expect(draft?.state.setupSnapshot?.instances[0]?.pileGroupId).toBeNull();
  });
});
