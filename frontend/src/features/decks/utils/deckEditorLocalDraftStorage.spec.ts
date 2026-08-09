import { afterEach, describe, expect, test } from 'vitest';
import type { DeckCardSummary } from '@/domain/decks/types';
import { createEmptyDeckForm } from '@/features/decks/composables/deckEditorDraftModel';
import {
  buildStoredDeckEditorDraft,
  createDeckEditorLocalDraftStorage,
  deckEditorDraftSlotToken,
  DECK_EDITOR_LOCAL_DRAFT_VERSION,
} from '@/features/decks/utils/deckEditorLocalDraftStorage';

const buildCard = (id: string, isHero = false): DeckCardSummary => ({
  id,
  result_type: 'card',
  key: id,
  label: id,
  is_hero: isHero,
  template_id: 'template-1',
  version_id: `${id}-version`,
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  name: id,
  type_line: isHero ? 'Hero' : 'Unit',
  mana_cost: '',
  mana_symbols: [],
  mana_value: 0,
  attack: null,
  health: null,
  rules_text: '',
  confidence: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  image_url: null,
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
});

describe('deckEditorLocalDraftStorage', () => {
  afterEach(() => localStorage.clear());

  test('stores the complete form and only referenced card snapshots', () => {
    const storage = createDeckEditorLocalDraftStorage();
    const form = createEmptyDeckForm();
    form.name = 'Local Deck';
    form.hero_card_id = 'hero-1';
    form.entries = [{ card_id: 'card-1', quantity: 2 }];
    form.sideboards = [{
      id: 'sideboard-local-1',
      name: 'Maybeboard',
      entries: [{ card_id: 'card-2', quantity: 1 }],
    }];
    const draft = buildStoredDeckEditorDraft('user-1', 'draft-1', form, {
      'hero-1': buildCard('hero-1', true),
      'card-1': buildCard('card-1'),
      'card-2': buildCard('card-2'),
      'browsed-only': buildCard('browsed-only'),
    });

    expect(storage.save(draft, { kind: 'empty' })).toEqual({ status: 'saved', draft });
    expect(Object.keys(draft.cards).sort()).toEqual(['card-1', 'card-2', 'hero-1']);
    expect(storage.read('user-1')).toEqual({
      status: 'loaded',
      slot: { kind: 'draft', draft },
    });
  });

  test('migrates a valid v1 draft to v2 on read', () => {
    const form = { ...createEmptyDeckForm(), name: 'Legacy Draft' };
    localStorage.setItem('card-reader.deck-editor.new-draft.user-1', JSON.stringify({
      version: 1,
      ownerId: 'user-1',
      savedAt: '2026-01-01T00:00:00Z',
      form,
      cards: {},
    }));

    const result = createDeckEditorLocalDraftStorage().read('user-1');

    expect(result.status).toBe('loaded');
    if (result.status !== 'loaded' || result.slot.kind !== 'draft') throw new Error('Expected draft');
    expect(result.slot.draft.version).toBe(DECK_EDITOR_LOCAL_DRAFT_VERSION);
    expect(result.slot.draft.form.name).toBe('Legacy Draft');
    expect(result.slot.draft.pendingCreateAttempt).toBeNull();
    expect(JSON.parse(localStorage.getItem('card-reader.deck-editor.new-draft.user-1') ?? '{}'))
      .toMatchObject({ version: 2, kind: 'draft' });
  });

  test('clears malformed and owner-mismatched data', () => {
    const storage = createDeckEditorLocalDraftStorage();
    localStorage.setItem('card-reader.deck-editor.new-draft.user-1', '{broken');
    expect(storage.read('user-1')).toEqual({ status: 'loaded', slot: { kind: 'empty' } });

    localStorage.setItem('card-reader.deck-editor.new-draft.user-1', JSON.stringify({
      version: 2,
      kind: 'draft',
      ownerId: 'user-2',
    }));
    expect(storage.read('user-1')).toEqual({ status: 'loaded', slot: { kind: 'empty' } });
    expect(localStorage.getItem('card-reader.deck-editor.new-draft.user-1')).toBeNull();
  });

  test('rejects stale conditional saves and discards', () => {
    const storage = createDeckEditorLocalDraftStorage();
    const first = buildStoredDeckEditorDraft(
      'user-1',
      'draft-1',
      { ...createEmptyDeckForm(), name: 'First' },
      {},
    );
    expect(storage.save(first, { kind: 'empty' }).status).toBe('saved');
    const second = buildStoredDeckEditorDraft(
      'user-1',
      'draft-1',
      { ...createEmptyDeckForm(), name: 'Second' },
      {},
    );
    expect(storage.save(second, deckEditorDraftSlotToken({ kind: 'draft', draft: first })).status)
      .toBe('saved');

    expect(storage.discard('user-1', { kind: 'draft', revision: first.revision }).status)
      .toBe('conflict');
    expect(storage.save(first, { kind: 'empty' }).status).toBe('conflict');
  });

  test('retires only the exact observed revision with a meaningful marker', () => {
    const storage = createDeckEditorLocalDraftStorage();
    const draft = buildStoredDeckEditorDraft(
      'user-1',
      'draft-1',
      { ...createEmptyDeckForm(), name: 'Created' },
      {},
    );
    storage.save(draft, { kind: 'empty' });

    const result = storage.retire(
      'user-1',
      draft.draftId,
      'deck-created',
      { kind: 'draft', revision: draft.revision },
    );

    expect(result.status).toBe('retired');
    expect(storage.read('user-1')).toEqual(result.status === 'retired'
      ? { status: 'loaded', slot: { kind: 'retired', marker: result.marker } }
      : null);
    if (result.status === 'retired') {
      expect(result.marker).toMatchObject({
        draftId: 'draft-1',
        revision: draft.revision,
        createdDeckId: 'deck-created',
      });
    }
  });

  test('returns unavailable instead of throwing when browser storage is blocked', () => {
    const localStorageDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      get: () => { throw new DOMException('Storage is blocked.', 'SecurityError'); },
    });
    try {
      expect(createDeckEditorLocalDraftStorage().read('user-1')).toEqual({ status: 'unavailable' });
    } finally {
      if (localStorageDescriptor) Object.defineProperty(globalThis, 'localStorage', localStorageDescriptor);
    }
  });
});
