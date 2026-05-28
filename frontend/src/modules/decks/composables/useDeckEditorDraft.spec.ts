import { describe, expect, test } from 'vitest';
import { ref } from 'vue';
import { useDeckEditorDraft, type BuilderStep } from '@/modules/decks/composables/useDeckEditorDraft';
import type { DeckCardSummary } from '@/modules/decks/types';

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

describe('useDeckEditorDraft', () => {
  test('builds a payload with named sideboards', () => {
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
      cardB: buildCard('cardB', 'Card B', 3),
    });
    const controller = useDeckEditorDraft({
      builderStep,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.name = 'Example';
    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 4 }];
    controller.addSideboard();
    const sideboardId = controller.activeBoardId.value;
    controller.renameSideboard(sideboardId, 'Flex');
    controller.handleGalleryAction({ ...cardLookup.value.cardB, result_type: 'card' });

    expect(controller.buildPayload()).toEqual({
      name: 'Example',
      description: null,
      visibility: 'private',
      hero_card_id: 'hero',
      entries: [{ card_id: 'cardA', quantity: 4 }],
      sideboards: [
        {
          name: 'Flex',
          entries: [{ card_id: 'cardB', quantity: 1 }],
        },
      ],
    });
  });

  test('targets add/remove actions at the active board', () => {
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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

  test('does not remove gallery cards during setup mode', () => {
    const builderStep = ref<BuilderStep>('setup');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 2 }];

    controller.handleGalleryRemoveAction('cardA');
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 2 }]);
  });

  test('board row action increments one copy on the active board', () => {
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
      cardLookup,
      rememberCards: () => undefined,
    });

    controller.form.hero_card_id = 'hero';
    controller.form.entries = [{ card_id: 'cardA', quantity: 2 }];

    controller.handleBoardRowAction('cardA');
    expect(controller.form.entries).toEqual([{ card_id: 'cardA', quantity: 3 }]);
  });

  test('board row action respects board-specific quantity limits', () => {
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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

  test('board row secondary action removes one copy without removing the entry', () => {
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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

  test('moves one copy from sideboard to mainboard', () => {
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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

  test('blocks row moves into mainboard when deck limits would be exceeded', () => {
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
      filler: buildCard('filler', 'Filler', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
      cardB: buildCard('cardB', 'Card B', 4),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      cardA: buildCard('cardA', 'Card A', 2),
      cardB: buildCard('cardB', 'Card B', 4),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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
    const builderStep = ref<BuilderStep>('build');
    const cardLookup = ref<Record<string, DeckCardSummary>>({
      hero: { ...buildCard('hero', 'Hero Card', 0), is_hero: true, type_line: 'Hero' },
      manaA: { ...buildCard('manaA', 'Mana A', 0), types: [{ id: 'mana', key: 'mana', label: 'Mana' }] },
      spellA: buildCard('spellA', 'Spell A', 2),
    });
    const controller = useDeckEditorDraft({
      builderStep,
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

