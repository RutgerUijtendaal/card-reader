import { afterEach, beforeEach, describe, expect, test } from 'vitest';
import type { DeckCardSummary } from '@/domain/decks/types';
import { createEmptyDeckForm } from '@/features/decks/composables/deckEditorDraftModel';
import {
  buildStoredDeckEditorDraft,
  createDeckEditorLocalDraftStorage,
  deckEditorDraftSlotToken,
  DECK_EDITOR_LOCAL_DRAFT_VERSION,
  type DeckEditorDraftLockManager,
} from '@/features/decks/utils/deckEditorLocalDraftStorage';

const createTestLockManager = (): DeckEditorDraftLockManager => {
  let queue = Promise.resolve();
  return {
    async request<Result>(
      _name: string,
      _options: { mode: 'exclusive' },
      callback: () => Result | PromiseLike<Result>,
    ): Promise<Result> {
      const previous = queue;
      let release!: () => void;
      queue = new Promise<void>((resolve) => {
        release = resolve;
      });
      await previous;
      try {
        return await callback();
      } finally {
        release();
      }
    },
  };
};

const buildCard = (id: string, isHero = false): DeckCardSummary => ({
  id,
  result_type: 'card',
  key: id,
  label: id,
  card_pool: 'player',
  card_roles: isHero ? ['hero'] : [],
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
  beforeEach(() => {
    Object.defineProperty(navigator, 'locks', {
      configurable: true,
      value: createTestLockManager(),
    });
  });
  afterEach(() => localStorage.clear());

  test('stores the complete form and only referenced card snapshots', async () => {
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

    await expect(storage.save(draft, { kind: 'empty' })).resolves.toEqual({ status: 'saved', draft });
    expect(Object.keys(draft.cards).sort()).toEqual(['card-1', 'card-2', 'hero-1']);
    expect(storage.read('user-1')).toEqual({
      status: 'loaded',
      slot: { kind: 'draft', draft },
    });
  });

  test('migrates a valid v1 draft to v2 on read and conditionally persists it', async () => {
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
      .toMatchObject({ version: 1 });
    await expect(createDeckEditorLocalDraftStorage().save(
      result.slot.draft,
      deckEditorDraftSlotToken(result.slot),
    )).resolves.toMatchObject({ status: 'saved' });
    expect(JSON.parse(localStorage.getItem('card-reader.deck-editor.new-draft.user-1') ?? '{}'))
      .toMatchObject({ version: 2, kind: 'draft' });
  });

  test('conditionally clears malformed and owner-mismatched data', async () => {
    const storage = createDeckEditorLocalDraftStorage();
    localStorage.setItem('card-reader.deck-editor.new-draft.user-1', '{broken');
    expect(storage.read('user-1')).toEqual({ status: 'loaded', slot: { kind: 'empty' } });
    await new Promise((resolve) => globalThis.setTimeout(resolve, 0));

    localStorage.setItem('card-reader.deck-editor.new-draft.user-1', JSON.stringify({
      version: 2,
      kind: 'draft',
      ownerId: 'user-2',
    }));
    expect(storage.read('user-1')).toEqual({ status: 'loaded', slot: { kind: 'empty' } });
    await new Promise((resolve) => globalThis.setTimeout(resolve, 0));
    expect(localStorage.getItem('card-reader.deck-editor.new-draft.user-1')).toBeNull();
  });

  test('rejects stale conditional saves and discards', async () => {
    const storage = createDeckEditorLocalDraftStorage();
    const first = buildStoredDeckEditorDraft(
      'user-1',
      'draft-1',
      { ...createEmptyDeckForm(), name: 'First' },
      {},
    );
    expect((await storage.save(first, { kind: 'empty' })).status).toBe('saved');
    const second = buildStoredDeckEditorDraft(
      'user-1',
      'draft-1',
      { ...createEmptyDeckForm(), name: 'Second' },
      {},
    );
    expect((await storage.save(second, deckEditorDraftSlotToken({ kind: 'draft', draft: first }))).status)
      .toBe('saved');

    expect((await storage.discard('user-1', { kind: 'draft', revision: first.revision })).status)
      .toBe('conflict');
    expect((await storage.save(first, { kind: 'empty' })).status).toBe('conflict');
  });

  test('retires only the exact observed revision with a meaningful marker', async () => {
    const storage = createDeckEditorLocalDraftStorage();
    const draft = buildStoredDeckEditorDraft(
      'user-1',
      'draft-1',
      { ...createEmptyDeckForm(), name: 'Created' },
      {},
    );
    await storage.save(draft, { kind: 'empty' });

    const result = await storage.retire(
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

  test('serializes competing conditional saves across tabs', async () => {
    const lockManager = createTestLockManager();
    const firstStorage = createDeckEditorLocalDraftStorage(localStorage, lockManager);
    const secondStorage = createDeckEditorLocalDraftStorage(localStorage, lockManager);
    const first = buildStoredDeckEditorDraft(
      'user-1',
      'draft-1',
      { ...createEmptyDeckForm(), name: 'First tab' },
      {},
    );
    const second = buildStoredDeckEditorDraft(
      'user-1',
      'draft-2',
      { ...createEmptyDeckForm(), name: 'Second tab' },
      {},
    );

    const results = await Promise.all([
      firstStorage.save(first, { kind: 'empty' }),
      secondStorage.save(second, { kind: 'empty' }),
    ]);

    expect(results.map((result) => result.status).sort()).toEqual(['conflict', 'saved']);
    expect(firstStorage.read('user-1')).toEqual({
      status: 'loaded',
      slot: { kind: 'draft', draft: first },
    });
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

  test('does not expose recoverable drafts when atomic locking is unavailable', async () => {
    const draft = buildStoredDeckEditorDraft(
      'user-1',
      'draft-without-locks',
      { ...createEmptyDeckForm(), name: 'Cannot Mutate Safely' },
      {},
    );
    localStorage.setItem(
      'card-reader.deck-editor.new-draft.user-1',
      JSON.stringify(draft),
    );
    const storage = createDeckEditorLocalDraftStorage(localStorage, null);

    expect(storage.read('user-1')).toEqual({ status: 'unavailable' });
    await expect(storage.discard(
      'user-1',
      { kind: 'draft', revision: draft.revision },
    )).resolves.toEqual({ status: 'unavailable' });
  });

  test('uses memory-only persistence when atomic browser locks are unavailable', async () => {
    const storage = createDeckEditorLocalDraftStorage(localStorage, null);
    const draft = buildStoredDeckEditorDraft(
      'user-1',
      'draft-1',
      { ...createEmptyDeckForm(), name: 'Memory only' },
      {},
    );

    await expect(storage.save(draft, { kind: 'empty' })).resolves.toEqual({
      status: 'unavailable',
    });
    expect(localStorage.getItem('card-reader.deck-editor.new-draft.user-1')).toBeNull();
  });
});
