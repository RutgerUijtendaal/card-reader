import { describe, expect, test, vi } from 'vitest';
import { ref } from 'vue';
import { useDeckEditorDraft, type DeckEditorMode } from '@/features/decks/composables/useDeckEditorDraft';
import { resolveDeckBuildingRules } from '@/domain/decks/utils/deckConstraints';
import type { DeckCardSummary, DeckRecord } from '@/domain/decks/types';

const buildCard = (id: string, name: string, manaValue = 1): DeckCardSummary =>
  ({
    id,
    result_type: 'card',
    key: id,
    label: name,
    is_hero: false,
    template_id: '',
    version_id: `${id}-version`,
    version_number: 1,
    previous_version_id: null,
    is_latest: true,
    name,
    type_line: 'Follower',
    mana_cost: '',
    mana_value: manaValue,
    mana_symbols: [],
    attack: null,
    health: null,
    rules_text: '',
    confidence: 1,
    created_at: '',
    updated_at: '',
    image_url: null,
    keywords: [],
    tags: [],
    symbols: [],
    types: [],
  }) satisfies DeckCardSummary;

const buildLegendaryCard = (id = 'legendary'): DeckCardSummary => ({
  ...buildCard(id, 'Legendary Card', 3),
  types: [{ id: 'legendary', key: 'legendary', label: 'Legendary' }],
});

describe('useDeckEditorDraft', () => {
  test('builds a payload with named sideboards', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
      cardB: buildCard('cardB', 'Card B', 3),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.name = 'Example';
    controller.form.hero_card_id = 'hero';
    controller.form.tag_ids = ['role-damage', 'type-armor'];
    controller.form.suggested_type_labels = ['Tempo Burst'];
    controller.form.entries = [{ card_id: 'cardA', quantity: 4 }];
    controller.addSideboard();
    const sideboardId = controller.activeBoardId.value;
    controller.renameSideboard(sideboardId, 'Flex');
    controller.handleGalleryAction({ ...cardLookup.value.cardB, result_type: 'card' });

    expect(controller.buildPayload()).toEqual({
      name: 'Example',
      description: null,
      long_description: null,
      difficulty: null,
      visibility: 'private',
      hero_card_id: 'hero',
      tag_ids: ['role-damage', 'type-armor'],
      suggested_type_labels: ['Tempo Burst'],
      entries: [{ card_id: 'cardA', quantity: 4 }],
      sideboards: [
        {
          name: 'Flex',
          entries: [{ card_id: 'cardB', quantity: 1 }],
        },
      ],
    });
  });

  test('hydrates and serializes a multiline long description', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const hero = { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' };
    const cardLookup = ref<Record<string, DeckCardSummary>>({ hero });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });
    const deck: DeckRecord = {
      id: 'deck-1',
      name: 'Example',
      description: 'Short summary',
      long_description: 'Opening plan\n\nSideboard notes',
      difficulty: 'medium',
      visibility: 'private',
      owner: { id: 'owner-1', username: 'owner' },
      hero_card: hero,
      mainboard: { total_cards: 0, unique_cards: 0, entries: [] },
      sideboards: [],
      totals: {
        overall_total_cards: 0,
        overall_unique_cards: 0,
        mainboard_total_cards: 0,
        mainboard_unique_cards: 0,
      },
      status: { is_valid: false, label: 'In Progress', issues: [] },
      created_at: '',
      updated_at: '',
    };

    controller.hydrateFromDeck(deck);

    expect(controller.form.long_description).toBe('Opening plan\n\nSideboard notes');
    expect(controller.form.difficulty).toBe('medium');

    controller.setDeckLongDescription('  Updated plan\n\nMore notes  ');
    controller.setDeckDifficulty('hard');

    expect(controller.buildPayload().long_description).toBe('Updated plan\n\nMore notes');
    expect(controller.buildPayload().difficulty).toBe('hard');
  });

  test('reorders mainboard entries and preserves the payload order', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
      cardB: buildCard('cardB', 'Card B', 3),
      cardC: buildCard('cardC', 'Card C', 4),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.name = 'Example';
    controller.form.hero_card_id = 'hero';
    controller.form.entries = [
      { card_id: 'cardA', quantity: 1 },
      { card_id: 'cardB', quantity: 2 },
      { card_id: 'cardC', quantity: 3 },
    ];

    controller.reorderEntries('mainboard', 'cardC', 'cardA');

    expect(controller.form.entries).toEqual([
      { card_id: 'cardC', quantity: 3 },
      { card_id: 'cardA', quantity: 1 },
      { card_id: 'cardB', quantity: 2 },
    ]);
    expect(controller.buildPayload().entries).toEqual([
      { card_id: 'cardC', quantity: 3 },
      { card_id: 'cardA', quantity: 1 },
      { card_id: 'cardB', quantity: 2 },
    ]);
  });

  test('reorders sideboard entries without changing the mainboard', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
      cardB: buildCard('cardB', 'Card B', 3),
      cardC: buildCard('cardC', 'Card C', 4),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.name = 'Example';
    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 1 }];
    controller.addSideboard();
    const sideboardId = controller.activeBoardId.value;
    controller.activeSideboard.value?.entries.push(
      { card_id: 'cardB', quantity: 2 },
      { card_id: 'cardC', quantity: 3 },
    );

    controller.reorderEntries(sideboardId, 'cardC', 'cardB');

    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 1 }]);
    expect(controller.activeSideboard.value?.entries).toEqual([
      { card_id: 'cardC', quantity: 3 },
      { card_id: 'cardB', quantity: 2 },
    ]);
    expect(controller.buildPayload().sideboards[0]?.entries).toEqual([
      { card_id: 'cardC', quantity: 3 },
      { card_id: 'cardB', quantity: 2 },
    ]);
  });

  test('targets add/remove actions at the active board', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.handleGalleryAction({ ...cardLookup.value.cardA, result_type: 'card' });
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 1 }]);

    controller.addSideboard();
    controller.handleGalleryAction({ ...cardLookup.value.cardA, result_type: 'card' });
    controller.handleGalleryRemoveAction('cardA');
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 1 }]);
    expect(controller.activeSideboard.value?.entries).toEqual([]);
  });

  test('removes one gallery copy at a time and deletes the final copy', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 3 }];

    controller.handleGalleryRemoveAction('cardA');
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 2 }]);

    controller.handleGalleryRemoveAction('cardA');
    controller.handleGalleryRemoveAction('cardA');
    expect(controller.form.entries).toEqual([]);
  });

  test('keeps a final removed row visible for the board entry animation window', () => {
    vi.useFakeTimers();
    try {
      const editorMode = ref<DeckEditorMode>('cards');
      const cardLookup = ref<Record<string, DeckCardSummary>>({
        hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
        cardA: buildCard('cardA', 'Card A', 2),
        cardB: buildCard('cardB', 'Card B', 3),
      });
      const controller = useDeckEditorDraft({
        editorMode,
        cardLookup,
        rememberCards: () => undefined,
      });

      controller.form.hero_card_id = 'hero';
      controller.form.entries = [
        { card_id: 'cardA', quantity: 1 },
        { card_id: 'cardB', quantity: 1 },
      ];

      controller.handleGalleryRemoveAction('cardA');

      expect(controller.form.entries).toEqual([{ card_id: 'cardB', quantity: 1 }]);
      expect(controller.detailedActiveBoardEntries.value).toEqual([
        { card: cardLookup.value.cardA, quantity: 1 },
        { card: cardLookup.value.cardB, quantity: 1 },
      ]);

      vi.advanceTimersByTime(320);

      expect(controller.detailedActiveBoardEntries.value).toEqual([
        { card: cardLookup.value.cardB, quantity: 1 },
      ]);
    } finally {
      vi.useRealTimers();
    }
  });

  test('does not remove gallery cards during setup mode', () => {
    const editorMode = ref<DeckEditorMode>('hero');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 2 }];

    controller.handleGalleryRemoveAction('cardA');
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 2 }]);
  });

  test('board row action increments one copy on the active board', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 2 }];

    controller.handleBoardRowAction('cardA');
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 3 }]);
  });

  test('board row action respects board-specific quantity limits', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 4 }];
    controller.handleBoardRowAction('cardA');
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 4 }]);

    controller.addSideboard();
    const sideboardId = controller.activeBoardId.value;
    controller.activeSideboard.value?.entries.push({ card_id: 'cardA', quantity: 100 });
    controller.handleBoardRowAction('cardA', sideboardId);
    expect(controller.activeSideboard.value?.entries).toEqual([{ card_id: 'cardA', quantity: 100 }]);
  });

  test('legendary cards warn without blocking actions by default', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const legendary = buildLegendaryCard();
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      legendary,
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.handleGalleryAction({ ...legendary, result_type: 'card' });
    controller.handleGalleryAction({ ...legendary, result_type: 'card' });
    expect(controller.form.entries).toEqual([{ card_id: 'legendary', quantity: 2 }]);

    controller.addSideboard();
    controller.handleGalleryAction({ ...legendary, result_type: 'card' });
    expect(controller.activeSideboard.value?.entries).toEqual([{ card_id: 'legendary', quantity: 1 }]);
    expect(controller.galleryActionDisabled({ ...legendary, result_type: 'card' })).toBe(false);
    expect(controller.warningMessages.value).toContain('Legendary cards are limited to 1 copy per deck.');
  });

  test('set quantity allows legendary cards above soft warning limits', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const legendary = buildLegendaryCard();
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      legendary,
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'legendary', quantity: 1 }];

    controller.setQuantity('legendary', '4');

    expect(controller.form.entries).toEqual([{ card_id: 'legendary', quantity: 4 }]);
    expect(controller.warningMessages.value).toContain('Legendary cards are limited to 1 copy per deck.');
  });

  test('reports legendary copy limit violations as warning messages by default', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const legendary = buildLegendaryCard();
    const manaA = { ...buildCard('manaA', 'Mana A', 0), types: [{ id: 'mana', key: 'mana', label: 'Mana' }] };
    const manaB = { ...buildCard('manaB', 'Mana B', 0), types: [{ id: 'mana', key: 'mana', label: 'Mana' }] };
    const manaC = { ...buildCard('manaC', 'Mana C', 0), types: [{ id: 'mana', key: 'mana', label: 'Mana' }] };
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      legendary,
      manaA,
      manaB,
      manaC,
      filler: buildCard('filler', 'Filler', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.name = 'Example';
    controller.form.hero_card_id = 'hero';
    controller.form.entries = [
      { card_id: 'legendary', quantity: 2 },
      { card_id: 'manaA', quantity: 4 },
      { card_id: 'manaB', quantity: 4 },
      { card_id: 'manaC', quantity: 4 },
      { card_id: 'filler', quantity: 6 },
    ];

    expect(controller.validationMessages.value).not.toContain('Legendary cards are limited to 1 copy per deck.');
    expect(controller.warningMessages.value).toContain('Legendary cards are limited to 1 copy per deck.');
  });

  test('uses hero override for mainboard copy limits', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: {
        ...buildCard('hero', 'Hero Card', 0),
        is_hero: true,
        type_line: 'Hero',
        deck_building_config: {
          overrides: {
            mainboard_copy_limit: { max: 6 },
          },
        },
      },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 5 }];

    expect(controller.getCardQuantityLimit('cardA')).toBe(6);
    expect(controller.validationMessages.value).not.toContain('Each mainboard card quantity must be between 1 and 4.');
  });

  test('uses self-targeted copy limits only for the owning card', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      selfLimited: {
        ...buildCard('selfLimited', 'Self Limited Card', 2),
        deck_building_config: {
          overrides: {
            mainboard_copy_limit: { applies_to: 'self', max: 6 },
          },
        },
      },
      defaultLimited: buildCard('defaultLimited', 'Default Limited Card', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'selfLimited', quantity: 5 }];

    expect(controller.getCardQuantityLimit('selfLimited')).toBe(6);
    expect(controller.getCardQuantityLimit('defaultLimited')).toBe(4);
    expect(controller.validationMessages.value).not.toContain('Each mainboard card quantity must be between 1 and 4.');

    controller.form.entries.push({ card_id: 'defaultLimited', quantity: 5 });

    expect(controller.validationMessages.value).toContain('Each mainboard card quantity must be between 1 and 4.');
  });

  test('resolves card overrides in deterministic card id order', () => {
    const repeated = {
      ...buildCard('repeated', 'Repeated Override', 2),
      deck_building_config: {
        overrides: {
          mainboard_copy_limit: { max: 6 },
        },
      },
    };
    const strict = {
      ...buildCard('strict', 'Strict Override', 2),
      deck_building_config: {
        overrides: {
          mainboard_copy_limit: { max: 1 },
        },
      },
    };

    const rules = resolveDeckBuildingRules({
      mainboardId: 'mainboard',
      heroCard: null,
      cardLookup: { repeated, strict },
      mainboardEntries: [{ card_id: 'repeated', quantity: 1 }],
      sideboards: [
        {
          id: 'sideboard',
          entries: [
            { card_id: 'strict', quantity: 1 },
            { card_id: 'repeated', quantity: 1 },
          ],
        },
      ],
    });

    expect(rules.mainboard_copy_limit.max).toBe(1);
  });

  test('uses backend numeric alias precedence for local rule resolution', () => {
    const hero = {
      ...buildCard('hero', 'Hero Card', 0),
      is_hero: true,
      type_line: 'Hero',
      deck_building_config: {
        overrides: {
          mana_type_count: { min: 10, count: 0 },
          mainboard_card_count: { max: 50, maximum: 25 },
        },
      },
    };

    const rules = resolveDeckBuildingRules({
      mainboardId: 'mainboard',
      heroCard: hero,
      cardLookup: { hero },
      mainboardEntries: [],
      sideboards: [],
    });

    expect(rules.mana_type_count.min).toBe(0);
    expect(rules.mainboard_card_count.max).toBe(25);
  });

  test('resolves mainboard count limits with the candidate card before adding', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const capRaiser = {
      ...buildCard('capRaiser', 'Cap Raiser', 2),
      deck_building_config: {
        overrides: {
          mainboard_card_count: { max: 101 },
        },
      },
    };
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      filler: buildCard('filler', 'Filler', 2),
      capRaiser,
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'filler', quantity: 100 }];

    expect(controller.galleryActionDisabled({ ...capRaiser, result_type: 'card' })).toBe(false);
    controller.handleGalleryAction({ ...capRaiser, result_type: 'card' });

    expect(controller.form.entries).toContainEqual({ card_id: 'capRaiser', quantity: 1 });
  });

  test('uses a candidate card lowering a blocking mainboard count limit before adding', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const capLowerer = {
      ...buildCard('capLowerer', 'Cap Lowerer', 2),
      deck_building_config: {
        overrides: {
          mainboard_card_count: { max: 50 },
        },
      },
    };
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      filler: buildCard('filler', 'Filler', 2),
      capLowerer,
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'filler', quantity: 99 }];

    expect(controller.galleryActionDisabled({ ...capLowerer, result_type: 'card' })).toBe(true);
    controller.handleGalleryAction({ ...capLowerer, result_type: 'card' });

    expect(controller.form.entries).not.toContainEqual({ card_id: 'capLowerer', quantity: 1 });
  });

  test('does not action-block soft mainboard card count limits', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: {
        ...buildCard('hero', 'Hero Card', 0),
        is_hero: true,
        type_line: 'Hero',
        deck_building_config: {
          overrides: {
            mainboard_card_count: { severity: 'soft', max: 1 },
          },
        },
      },
      filler: buildCard('filler', 'Filler', 2),
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'filler', quantity: 100 }];

    expect(controller.galleryActionDisabled({ ...cardLookup.value.cardA, result_type: 'card' })).toBe(false);
    controller.handleGalleryAction({ ...cardLookup.value.cardA, result_type: 'card' });

    expect(controller.form.entries).toContainEqual({ card_id: 'cardA', quantity: 1 });
    expect(controller.warningMessages.value).toContain('Deck cannot contain more than 1 mainboard cards.');
  });

  test('blocks sideboard copies when mainboard copy limit is scoped to the whole deck', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: {
        ...buildCard('hero', 'Hero Card', 0),
        is_hero: true,
        type_line: 'Hero',
        deck_building_config: {
          overrides: {
            mainboard_copy_limit: { scope: 'whole_deck', max: 4 },
          },
        },
      },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 4 }];
    controller.addSideboard();

    expect(controller.getCardQuantityLimit('cardA')).toBe(0);
    expect(controller.galleryActionDisabled({ ...cardLookup.value.cardA, result_type: 'card' })).toBe(true);
    controller.handleGalleryAction({ ...cardLookup.value.cardA, result_type: 'card' });
    expect(controller.activeSideboard.value?.entries).toEqual([]);
  });

  test('applies candidate self copy limits before sideboard adds', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const candidate: DeckCardSummary = {
      ...buildCard('candidate', 'Candidate Card', 2),
      deck_building_config: {
        overrides: {
          mainboard_copy_limit: { applies_to: 'self', scope: 'whole_deck', max: 1 },
        },
      },
    };
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      candidate,
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'candidate', quantity: 1 }];
    controller.addSideboard();

    expect(controller.getCardQuantityLimit('candidate')).toBe(0);
    expect(controller.galleryActionDisabled({ ...candidate, result_type: 'card' })).toBe(true);
  });

  test('uses whole-deck mainboard card count scope for mainboard add gates', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: {
        ...buildCard('hero', 'Hero Card', 0),
        is_hero: true,
        type_line: 'Hero',
        deck_building_config: {
          overrides: {
            mainboard_card_count: { scope: 'whole_deck', max: 100 },
          },
        },
      },
      main: buildCard('main', 'Main Card', 2),
      side: buildCard('side', 'Side Card', 2),
      candidate: buildCard('candidate', 'Candidate Card', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'main', quantity: 80 }];
    controller.addSideboard();
    controller.activeSideboard.value?.entries.push({ card_id: 'side', quantity: 20 });
    controller.selectBoard('mainboard');

    expect(controller.galleryActionDisabled({ ...cardLookup.value.candidate, result_type: 'card' })).toBe(true);
    controller.handleGalleryAction({ ...cardLookup.value.candidate, result_type: 'card' });
    expect(controller.form.entries).not.toContainEqual({ card_id: 'candidate', quantity: 1 });
  });

  test('reports action-blocking messages when a selected hero lowers an existing copy limit', () => {
    const editorMode = ref<DeckEditorMode>('hero');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      strictHero: {
        ...buildCard('strictHero', 'Strict Hero', 0),
        is_hero: true,
        type_line: 'Hero',
        deck_building_config: {
          overrides: {
            mainboard_copy_limit: { max: 4 },
          },
        },
      },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.name = 'Example';
    controller.form.hero_card_id = 'strictHero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 6 }];

    expect(controller.blockingMessages.value).toContain(
      'Each mainboard card quantity must be between 1 and 4.',
    );
    expect(controller.setupMessages.value).toEqual([]);
  });

  test('does not treat validity-only deck constraints as setup blockers', () => {
    const editorMode = ref<DeckEditorMode>('hero');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.name = 'Example';
    controller.form.hero_card_id = 'hero';
    controller.form.entries = [];

    expect(controller.validationMessages.value).toContain(
      'Deck must contain at least 20 mainboard cards.',
    );
    expect(controller.blockingMessages.value).toEqual([]);
  });

  test('does not show a setup issue when no hero is selected', () => {
    const editorMode = ref<DeckEditorMode>('hero');
    const cardLookup = ref<Record<string, DeckCardSummary>>({});
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.name = 'Example';
    controller.form.hero_card_id = '';

    expect(controller.setupMessages.value).toEqual([]);
  });

  test('does not show a setup issue when deck name is empty', () => {
    const editorMode = ref<DeckEditorMode>('hero');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.name = '';
    controller.form.hero_card_id = 'hero';

    expect(controller.setupMessages.value).toEqual([]);
  });

  test('uses whole deck scope for hard legendary action limits', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const legendary = buildLegendaryCard();
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: {
        ...buildCard('hero', 'Hero Card', 0),
        is_hero: true,
        type_line: 'Hero',
        deck_building_config: {
          overrides: {
            legendary_copy_limit: { severity: 'hard', blocks_action: true, scope: 'whole_deck' },
          },
        },
      },
      legendary,
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'legendary', quantity: 1 }];
    controller.addSideboard();

    expect(controller.getCardQuantityLimit('legendary')).toBe(0);
  });

  test('does not apply mainboard-scoped hard legendary action limits to sideboard edits', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const legendary = buildLegendaryCard();
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: {
        ...buildCard('hero', 'Hero Card', 0),
        is_hero: true,
        type_line: 'Hero',
        deck_building_config: {
          overrides: {
            legendary_copy_limit: { severity: 'hard', blocks_action: true },
          },
        },
      },
      legendary,
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'legendary', quantity: 1 }];
    controller.addSideboard();

    expect(controller.getCardQuantityLimit('legendary')).toBe(100);
    expect(controller.galleryActionDisabled({ ...legendary, result_type: 'card' })).toBe(false);
  });

  test('board row secondary action removes one copy without removing the entry', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 3 }];

    controller.handleBoardRowSecondaryAction('cardA');
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 2 }]);

    controller.handleBoardRowSecondaryAction('cardA');
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 1 }]);

    controller.handleBoardRowSecondaryAction('cardA');
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 1 }]);
  });

  test('board row actions target the active sideboard when selected', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 2 }];
    controller.addSideboard();
    controller.activeSideboard.value?.entries.push({ card_id: 'cardA', quantity: 3 });

    controller.handleBoardRowAction('cardA');
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 2 }]);
    expect(controller.activeSideboard.value?.entries).toEqual([{ card_id: 'cardA', quantity: 4 }]);

    controller.handleBoardRowSecondaryAction('cardA');
    expect(controller.activeSideboard.value?.entries).toEqual([{ card_id: 'cardA', quantity: 3 }]);
  });

  test('moves one copy from mainboard to sideboard', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 3 }];
    controller.addSideboard();
    const destinationBoardId = controller.activeBoardId.value;

    expect(controller.moveEntryToBoard('cardA', destinationBoardId, 'mainboard')).toBe(true);
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 2 }]);
    expect(controller.activeSideboard.value?.entries).toEqual([{ card_id: 'cardA', quantity: 1 }]);
  });

  test('allows moving the only legendary copy between boards', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const legendary = buildLegendaryCard();
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: {
        ...buildCard('hero', 'Hero Card', 0),
        is_hero: true,
        type_line: 'Hero',
        deck_building_config: {
          overrides: {
            legendary_copy_limit: { severity: 'hard', blocks_action: true, scope: 'whole_deck' },
          },
        },
      },
      legendary,
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'legendary', quantity: 1 }];
    controller.addSideboard();
    const destinationBoardId = controller.activeBoardId.value;

    expect(controller.moveEntryToBoard('legendary', destinationBoardId, 'mainboard')).toBe(true);
    expect(controller.form.entries).toEqual([]);
    expect(controller.activeSideboard.value?.entries).toEqual([{ card_id: 'legendary', quantity: 1 }]);
  });

  test('moves one copy from sideboard to mainboard', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.addSideboard();
    const sourceBoardId = controller.activeBoardId.value;
    controller.activeSideboard.value?.entries.push({ card_id: 'cardA', quantity: 2 });

    expect(controller.moveEntryToBoard('cardA', 'mainboard', sourceBoardId)).toBe(true);
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 1 }]);
    expect(controller.activeSideboard.value?.entries).toEqual([{ card_id: 'cardA', quantity: 1 }]);
  });

  test('merges one moved copy into an existing destination row when valid', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 2 }];
    controller.addSideboard();
    const destinationBoardId = controller.activeBoardId.value;
    controller.activeSideboard.value?.entries.push({ card_id: 'cardA', quantity: 3 });

    expect(controller.moveEntryToBoard('cardA', destinationBoardId, 'mainboard')).toBe(true);
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 1 }]);
    expect(controller.activeSideboard.value?.entries).toEqual([{ card_id: 'cardA', quantity: 4 }]);
  });

  test('blocks row moves when destination limits would be exceeded', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 2 }];
    controller.addSideboard();
    const destinationBoardId = controller.activeBoardId.value;
    controller.activeSideboard.value?.entries.push({ card_id: 'cardA', quantity: 100 });

    expect(controller.moveEntryToBoard('cardA', destinationBoardId, 'mainboard')).toBe(false);
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 2 }]);
    expect(controller.activeSideboard.value?.entries).toEqual([{ card_id: 'cardA', quantity: 100 }]);
  });

  test('blocks moving legendary cards into a board when another copy remains elsewhere', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const legendary = buildLegendaryCard();
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: {
        ...buildCard('hero', 'Hero Card', 0),
        is_hero: true,
        type_line: 'Hero',
        deck_building_config: {
          overrides: {
            legendary_copy_limit: { severity: 'hard', blocks_action: true, scope: 'whole_deck' },
          },
        },
      },
      legendary,
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'legendary', quantity: 1 }];
    controller.addSideboard();
    const sourceBoardId = controller.activeBoardId.value;
    controller.activeSideboard.value?.entries.push({ card_id: 'legendary', quantity: 1 });

    expect(controller.moveEntryToBoard('legendary', 'mainboard', sourceBoardId)).toBe(false);
    expect(controller.getMoveEntryToBoardValidationError('legendary', 'mainboard', sourceBoardId)).toBe(
      'Legendary cards are limited to 1 copy per deck.',
    );
  });

  test('blocks row moves into mainboard when deck limits would be exceeded', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
      filler: buildCard('filler', 'Filler', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [
      { card_id: 'cardA', quantity: 4 },
      { card_id: 'filler', quantity: 36 },
    ];
    controller.addSideboard();
    const sourceBoardId = controller.activeBoardId.value;
    controller.activeSideboard.value?.entries.push({ card_id: 'cardA', quantity: 1 });

    expect(controller.moveEntryToBoard('cardA', 'mainboard', sourceBoardId)).toBe(false);
    expect(controller.form.entries).toEqual([
      { card_id: 'cardA', quantity: 4 },
      { card_id: 'filler', quantity: 36 },
    ]);
    expect(controller.activeSideboard.value?.entries).toEqual([{ card_id: 'cardA', quantity: 1 }]);
  });

  test('returns move destinations for other boards only', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 2 }];
    controller.addSideboard();
    controller.addSideboard();
    const firstSideboardId = controller.sideboardTabs.value[0]?.id ?? '';
    const secondSideboardId = controller.sideboardTabs.value[1]?.id ?? '';

    expect(controller.getBoardMoveDestinations('cardA', 'mainboard').map((item) => item.boardId)).toEqual([
      firstSideboardId,
      secondSideboardId,
    ]);
    expect(controller.getBoardMoveDestinations('cardA', firstSideboardId).map((item) => item.boardId)).toEqual([
      'mainboard',
      secondSideboardId,
    ]);
  });

  test('tracks mainboard and overall totals separately', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
      cardB: buildCard('cardB', 'Card B', 4),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 40 }];
    controller.addSideboard();
    controller.handleGalleryAction({ ...cardLookup.value.cardB, result_type: 'card' });
    controller.changeQuantity('cardB', 4);

    expect(controller.totalMainboardCards.value).toBe(40);
    expect(controller.overallTotalCards.value).toBe(45);
    expect(controller.sideboardTabs.value[0]?.totalCards).toBe(5);
  });

  test('deduplicates overall unique cards across mainboard and sideboards', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
      cardB: buildCard('cardB', 'Card B', 4),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 4 }];
    controller.addSideboard();
    controller.activeSideboard.value?.entries.push(
      { card_id: 'cardA', quantity: 2 },
      { card_id: 'cardB', quantity: 1 },
    );

    expect(controller.overallUniqueCards.value).toBe(2);
  });

  test('flags whether mainboard Mana cards reach the free mulligan threshold', () => {
    const editorMode = ref<DeckEditorMode>('cards');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      manaA: { ...buildCard('manaA', 'Mana A', 0), types: [{ id: 'mana', key: 'mana', label: 'Mana' }] },
      spellA: buildCard('spellA', 'Spell A', 2),
    });
    const controller = useDeckEditorDraft({
      editorMode,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [
      { card_id: 'manaA', quantity: 1 },
      { card_id: 'spellA', quantity: 3 },
    ];
    expect(controller.hasFreeMulliganManaRatio.value).toBe(true);

    controller.form.entries = [
      { card_id: 'manaA', quantity: 1 },
      { card_id: 'spellA', quantity: 4 },
    ];
    expect(controller.hasFreeMulliganManaRatio.value).toBe(false);
  });
});
