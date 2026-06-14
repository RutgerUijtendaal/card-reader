import { describe, expect, test, beforeEach } from 'vitest';
import { createLocalPlaytestStorage } from '@/modules/playtester/localPlaytestStorage';
import type { StoredPlaytestDraft } from '@/modules/playtester/types';
import type { DeckCardSummary } from '@/modules/decks/types';

const card: DeckCardSummary = {
  id: 'card-1',
  key: 'card-1',
  label: 'Card 1',
  result_type: 'card',
  image_url: null,
  is_hero: false,
  lifecycle_status: 'active',
  template_id: '',
  version_id: 'card-1-version',
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  name: 'Card 1',
  type_line: '',
  mana_cost: '',
  mana_symbols: [],
  mana_value: 1,
  attack: null,
  health: null,
  rules_text: '',
  confidence: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
};

describe('localPlaytestStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('loads current-version drafts', () => {
    const storage = createLocalPlaytestStorage();
    const draft: StoredPlaytestDraft = {
      version: 2,
      deckId: 'deck-1',
      deckUpdatedAt: '2026-01-01T00:00:00Z',
      savedAt: '2026-01-01T00:00:00Z',
      state: {
        deckId: 'deck-1',
        deckUpdatedAt: '2026-01-01T00:00:00Z',
        phase: 'opening',
        handSize: 7,
        stackFaces: { library: 'back' },
        openingSetup: {
          selectedManaInstanceIds: [],
          selectedSetupInstanceIds: [],
          reservedOrigins: {},
          reservedOriginOrders: {},
        },
        setupSnapshot: {
          instances: [
            {
              instanceId: 'card-1:main:1',
              cardId: 'card-1',
              card,
              zoneId: 'library',
              order: 0,
              tapped: false,
              face: 'front',
              setupOrigin: false,
              boardX: null,
              boardY: null,
              pileGroupId: null,
              pileOrder: null,
            },
          ],
        },
        instances: [
          {
            instanceId: 'card-1:main:1',
            cardId: 'card-1',
            card,
            zoneId: 'library',
            order: 0,
            tapped: false,
            face: 'front',
            setupOrigin: false,
            boardX: null,
            boardY: null,
            pileGroupId: null,
            pileOrder: null,
          },
        ],
      },
    };
    localStorage.setItem('card-reader.playtester.deck-1', JSON.stringify(draft));

    expect(storage.load('deck-1')).toEqual(draft);
  });

  test('ignores unsupported draft versions', () => {
    const storage = createLocalPlaytestStorage();
    localStorage.setItem('card-reader.playtester.deck-1', JSON.stringify({
      version: 99,
      deckId: 'deck-1',
      state: {},
    }));

    expect(storage.load('deck-1')).toBeNull();
  });

  test('migrates version 1 drafts with missing card faces', () => {
    const storage = createLocalPlaytestStorage();
    localStorage.setItem('card-reader.playtester.deck-1', JSON.stringify({
      version: 1,
      deckId: 'deck-1',
      deckUpdatedAt: '2026-01-01T00:00:00Z',
      savedAt: '2026-01-01T00:00:00Z',
      state: {
        deckId: 'deck-1',
        deckUpdatedAt: '2026-01-01T00:00:00Z',
        phase: 'play',
        handSize: 7,
        stackFaces: { library: 'back' },
        openingSetup: {
          selectedManaInstanceIds: [],
          selectedSetupInstanceIds: [],
        },
        setupSnapshot: null,
        instances: [
          {
            instanceId: 'card-1:main:1',
            cardId: 'card-1',
            card,
            zoneId: 'library',
            order: 0,
            tapped: false,
            setupOrigin: false,
            boardX: null,
            boardY: null,
            pileGroupId: null,
            pileOrder: null,
          },
        ],
      },
    }));

    const migrated = storage.load('deck-1');

    expect(migrated?.version).toBe(2);
    expect(migrated?.state.instances[0]?.face).toBe('front');
  });
});
