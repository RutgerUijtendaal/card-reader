import { afterEach, describe, expect, test } from 'vitest';
import type { DeckCardSummary } from '@/domain/decks/types';
import { createEmptyDeckForm } from '@/features/decks/composables/deckEditorDraftModel';
import {
  createDeckEditorLocalDraftStorage,
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
  afterEach(() => {
    localStorage.clear();
  });

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
    const draft = storage.save('user-1', form, {
      'hero-1': buildCard('hero-1', true),
      'card-1': buildCard('card-1'),
      'card-2': buildCard('card-2'),
      'browsed-only': buildCard('browsed-only'),
    });

    expect(draft.version).toBe(DECK_EDITOR_LOCAL_DRAFT_VERSION);
    expect(Object.keys(draft.cards).sort()).toEqual(['card-1', 'card-2', 'hero-1']);
    expect(storage.load('user-1')).toEqual(draft);
    expect(draft.form.sideboards[0]?.id).toBe('sideboard-local-1');
  });

  test('clears malformed and owner-mismatched drafts', () => {
    const storage = createDeckEditorLocalDraftStorage();
    localStorage.setItem('card-reader.deck-editor.new-draft.user-1', '{broken');

    expect(storage.load('user-1')).toBeNull();
    expect(localStorage.getItem('card-reader.deck-editor.new-draft.user-1')).toBeNull();

    localStorage.setItem('card-reader.deck-editor.new-draft.user-1', JSON.stringify({
      version: DECK_EDITOR_LOCAL_DRAFT_VERSION,
      ownerId: 'user-2',
      savedAt: '2026-01-01T00:00:00Z',
      form: createEmptyDeckForm(),
      cards: {},
    }));

    expect(storage.load('user-1')).toBeNull();
    expect(localStorage.getItem('card-reader.deck-editor.new-draft.user-1')).toBeNull();
  });

  test('clears a stored draft explicitly', () => {
    const storage = createDeckEditorLocalDraftStorage();
    storage.save('user-1', { ...createEmptyDeckForm(), name: 'Local Deck' }, {});

    storage.clear('user-1');

    expect(storage.load('user-1')).toBeNull();
  });
});
