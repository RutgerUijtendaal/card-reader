import { describe, expect, test } from 'vitest';
import {
  addInstanceToVisualPile,
  acceptOpeningSetup,
  cloneCardInstance,
  cloneCardInstances,
  cloneCardInstanceSnapshots,
  countZone,
  createInitialPlaytestState,
  deleteCardInstances,
  drawOpeningHand,
  drawCards,
  getOpeningManaInstances,
  getOpeningSetupInstances,
  getZoneInstances,
  isManaCardInstance,
  isSetupCardInstance,
  isStoredDraftStale,
  moveBoardInstancesByDelta,
  moveInstanceToZone,
  mulliganOpeningHand,
  placeInstanceOnBoard,
  removeInstanceFromVisualPile,
  resetToSetup,
  serializePlaytestDraft,
  setOpeningHandSize,
  setOpeningStep,
  stageOpeningSetupCardForPlay,
  shuffleZone,
  startNextTurn,
  toggleCardFace,
  toggleCardsFace,
  toggleOpeningSetupHandled,
  toggleTapped,
  toggleOpeningManaSelection,
} from '@/modules/playtester/playtestState';
import type { DeckCardSummary, DeckMetadataOption, DeckRecord } from '@/modules/decks/types';

const buildCard = (
  id: string,
  name: string,
  options: { keywords?: string[]; types?: DeckMetadataOption[] } = {},
): DeckCardSummary => ({
  id,
  key: id,
  label: name,
  result_type: 'card',
  image_url: null,
  is_hero: false,
  lifecycle_status: 'active',
  template_id: '',
  version_id: id,
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  name,
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
  keywords: options.keywords ?? [],
  tags: [],
  symbols: [],
  types: options.types ?? [],
});

const buildDeck = (): DeckRecord => ({
  id: 'deck-1',
  name: 'Test Deck',
  description: null,
  visibility: 'public',
  owner: { id: 'user-1', username: 'owner' },
  hero_card: { ...buildCard('hero', 'Hero'), is_hero: true },
  mainboard: {
    total_cards: 12,
    unique_cards: 4,
    entries: [
      { quantity: 2, card: buildCard('setup-card', 'Setup Card', { keywords: ['Setup'] }) },
      { quantity: 3, card: buildCard('mana-card', 'Mana Card', { types: [{ id: 'mana', key: 'mana', label: 'Mana' }] }) },
      { quantity: 6, card: buildCard('cheap-card', 'Cheap Card') },
      { quantity: 1, card: buildCard('late-card', 'Late Card') },
    ],
  },
  sideboards: [],
  totals: {
    overall_total_cards: 12,
    overall_unique_cards: 4,
    mainboard_total_cards: 12,
    mainboard_unique_cards: 4,
  },
  status: {
    is_valid: true,
    label: 'Ready',
    issues: [],
  },
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
});

const noShuffle = () => 0;

describe('playtestState', () => {
  test('expands deck quantities, starts mana-first, and keeps hero outside the library', () => {
    const state = createInitialPlaytestState(buildDeck(), noShuffle);

    expect(state.phase).toBe('opening');
    expect(state.openingSetup.step).toBe('mana');
    expect(countZone(state, 'hero')).toBe(1);
    expect(countZone(state, 'hand')).toBe(0);
    expect(countZone(state, 'library')).toBe(12);
    expect(new Set(state.instances.map((instance) => instance.instanceId)).size).toBe(13);
    expect(getZoneInstances(state, 'hero')[0]?.card.name).toBe('Hero');
    expect(state.instances.every((instance) => instance.pileGroupId === null && instance.pileOrder === null)).toBe(true);
    expect(state.instances.every((instance) => instance.face === 'front')).toBe(true);
  });

  test('draws, moves, taps, and resets without duplicating card instances', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const playing = acceptOpeningSetup(drawOpeningHand(initial));
    const handCard = getZoneInstances(playing, 'hand')[0];
    if (!handCard) {
      throw new Error('expected hand card');
    }

    const inPlay = moveInstanceToZone(playing, handCard.instanceId, 'play');
    const tapped = toggleTapped(inPlay, handCard.instanceId);

    expect(getZoneInstances(tapped, 'play')[0]?.tapped).toBe(true);
    expect(new Set(tapped.instances.map((instance) => instance.instanceId)).size).toBe(tapped.instances.length);
  });

  test('places cards on the board with bounded coordinates', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const card = getZoneInstances(initial, 'library')[0];
    if (!card) {
      throw new Error('expected library card');
    }

    const placed = placeInstanceOnBoard(initial, card.instanceId, 110, -12);
    const boardCard = getZoneInstances(placed, 'play')[0];

    expect(boardCard?.instanceId).toBe(card.instanceId);
    expect(boardCard?.boardX).toBe(100);
    expect(boardCard?.boardY).toBe(0);
    expect(countZone(placed, 'library')).toBe(11);
  });

  test('moves multiple board cards by a shared bounded delta', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const [first, second, third] = getZoneInstances(initial, 'library');
    if (!first || !second || !third) {
      throw new Error('expected library cards');
    }
    const placed = [first, second, third].reduce(
      (state, instance, index) => placeInstanceOnBoard(state, instance.instanceId, 20 + index * 12, 30 + index * 8),
      initial,
    );

    const moved = moveBoardInstancesByDelta(placed, [first.instanceId, third.instanceId], 15, -40);

    expect(moved.instances.find((instance) => instance.instanceId === first.instanceId)?.boardX).toBe(35);
    expect(moved.instances.find((instance) => instance.instanceId === first.instanceId)?.boardY).toBe(0);
    expect(moved.instances.find((instance) => instance.instanceId === second.instanceId)?.boardX).toBe(32);
    expect(moved.instances.find((instance) => instance.instanceId === second.instanceId)?.boardY).toBe(38);
    expect(moved.instances.find((instance) => instance.instanceId === third.instanceId)?.boardX).toBe(59);
    expect(moved.instances.find((instance) => instance.instanceId === third.instanceId)?.boardY).toBe(6);
  });

  test('detects mana and Setup physical instances', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);

    expect(getOpeningManaInstances(initial)).toHaveLength(3);
    expect(getOpeningSetupInstances(initial)).toHaveLength(2);
    expect(getOpeningManaInstances(initial).every(isManaCardInstance)).toBe(true);
    expect(getOpeningSetupInstances(initial).every(isSetupCardInstance)).toBe(true);
  });

  test('selecting opening mana reserves the exact instance without drawing hand', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const mana = getOpeningManaInstances(initial)[0];
    if (!mana) {
      throw new Error('expected mana card');
    }

    const selected = toggleOpeningManaSelection(initial, mana.instanceId, true);

    expect(selected.openingSetup.selectedManaInstanceIds).toEqual([mana.instanceId]);
    expect(selected.instances.find((instance) => instance.instanceId === mana.instanceId)?.zoneId).toBe('other');
    expect(getZoneInstances(selected, 'hand')).toHaveLength(0);

    const deselected = toggleOpeningManaSelection(selected, mana.instanceId, false);

    expect(deselected.openingSetup.selectedManaInstanceIds).toEqual([]);
    expect(deselected.instances.find((instance) => instance.instanceId === mana.instanceId)?.zoneId).toBe('library');
    expect(getZoneInstances(deselected, 'hand')).toHaveLength(0);
  });

  test('opening mulligan preserves reserved mana and leaves Setup hints unreserved', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const mana = getOpeningManaInstances(initial)[0];
    const setup = getOpeningSetupInstances(initial)[0];
    if (!mana || !setup) {
      throw new Error('expected opening selections');
    }
    const reserved = drawOpeningHand(toggleOpeningManaSelection(initial, mana.instanceId, true));

    const afterMulligan = mulliganOpeningHand(reserved, noShuffle);

    expect(afterMulligan.openingSetup.mulliganCount).toBe(1);
    expect(afterMulligan.openingSetup.selectedManaInstanceIds).toEqual([mana.instanceId]);
    expect(afterMulligan.openingSetup.selectedSetupInstanceIds).toEqual([]);
    expect(afterMulligan.instances.find((instance) => instance.instanceId === mana.instanceId)?.zoneId).toBe('other');
    expect(afterMulligan.instances.find((instance) => instance.instanceId === setup.instanceId)?.zoneId).not.toBe('other');
    expect(getZoneInstances(afterMulligan, 'hand')).toHaveLength(7);
    expect(getZoneInstances(afterMulligan, 'hand').some((instance) =>
      instance.instanceId === mana.instanceId,
    )).toBe(false);
  });

  test('opening Setup cards are hints, not selectable reservations', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const setup = getOpeningSetupInstances(initial)[0];
    if (!setup) {
      throw new Error('expected Setup card');
    }

    const afterMulligan = mulliganOpeningHand(drawOpeningHand({
      ...initial,
      openingSetup: {
        ...initial.openingSetup,
        selectedSetupInstanceIds: [setup.instanceId],
        reservedOrigins: { [setup.instanceId]: setup.zoneId },
        reservedOriginOrders: { [setup.instanceId]: setup.order },
      },
    }), noShuffle);

    expect(afterMulligan.openingSetup.selectedSetupInstanceIds).toEqual([]);
    expect(afterMulligan.openingSetup.reservedOrigins).toEqual({});
    expect(afterMulligan.instances.find((instance) => instance.instanceId === setup.instanceId)?.zoneId).not.toBe('other');
  });

  test('opening Setup handled markers are persisted by card identity', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const setup = getOpeningSetupInstances(initial)[0];
    if (!setup) {
      throw new Error('expected Setup card');
    }

    const handled = toggleOpeningSetupHandled(initial, setup.cardId, true);
    const unhandled = toggleOpeningSetupHandled(handled, setup.cardId, false);

    expect(handled.openingSetup.handledSetupCardIds).toEqual([setup.cardId]);
    expect(unhandled.openingSetup.handledSetupCardIds).toEqual([]);
  });

  test('opening mulligan preserves setup-action cards moved into hand', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const mana = getOpeningManaInstances(initial)[0];
    const setupActionCard = getZoneInstances(initial, 'library')
      .find((instance) => !isManaCardInstance(instance) && !isSetupCardInstance(instance));
    if (!mana || !setupActionCard) {
      throw new Error('expected opening mana and setup action card');
    }
    const selected = toggleOpeningManaSelection(initial, mana.instanceId, true);
    const movedToHand = moveInstanceToZone(selected, setupActionCard.instanceId, 'hand');
    const markedSetupAction = {
      ...movedToHand,
      instances: movedToHand.instances.map((instance) =>
        instance.instanceId === setupActionCard.instanceId
          ? { ...instance, setupOrigin: true }
          : instance,
      ),
    };
    const drawn = drawOpeningHand(markedSetupAction);

    const afterMulligan = mulliganOpeningHand(drawn, noShuffle);

    expect(afterMulligan.instances.find((instance) => instance.instanceId === setupActionCard.instanceId)?.zoneId).toBe('hand');
    expect(getZoneInstances(afterMulligan, 'hand')).toHaveLength(7);
  });

  test('stepping back from opening hand clears drawn hand cards but preserves setup hand cards', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const setupActionCard = getZoneInstances(initial, 'library')
      .find((instance) => !isManaCardInstance(instance) && !isSetupCardInstance(instance));
    if (!setupActionCard) {
      throw new Error('expected setup action card');
    }
    const movedToHand = moveInstanceToZone(initial, setupActionCard.instanceId, 'hand');
    const markedSetupAction = {
      ...movedToHand,
      instances: movedToHand.instances.map((instance) =>
        instance.instanceId === setupActionCard.instanceId
          ? { ...instance, setupOrigin: true }
          : instance,
      ),
    };
    const drawn = drawOpeningHand(markedSetupAction);

    const backToSetup = setOpeningStep(drawn, 'setup');

    expect(getZoneInstances(backToSetup, 'hand').map((instance) => instance.instanceId)).toEqual([setupActionCard.instanceId]);
    expect(getZoneInstances(backToSetup, 'library')).toHaveLength(getZoneInstances(initial, 'library').length - 1);
    expect(drawOpeningHand(backToSetup).openingSetup.step).toBe('hand');
    expect(getZoneInstances(drawOpeningHand(backToSetup), 'hand')).toHaveLength(7);
  });

  test('opening setup Play action stages cards until the hand is kept', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const mana = getOpeningManaInstances(initial).slice(0, 3);
    const setupActionCard = getZoneInstances(initial, 'library')
      .find((instance) => !isManaCardInstance(instance) && !isSetupCardInstance(instance));
    if (mana.length !== 3 || !setupActionCard) {
      throw new Error('expected opening mana and setup action card');
    }
    const selected = mana.reduce(
      (state, instance) => toggleOpeningManaSelection(state, instance.instanceId, true),
      initial,
    );
    const staged = stageOpeningSetupCardForPlay(selected, setupActionCard.instanceId);

    expect(staged.openingSetup.selectedSetupInstanceIds).toEqual([setupActionCard.instanceId]);
    expect(staged.instances.find((instance) => instance.instanceId === setupActionCard.instanceId)?.zoneId).toBe('other');
    expect(getZoneInstances(staged, 'play')).toHaveLength(0);

    const drawn = drawOpeningHand(staged);

    expect(drawn.openingSetup.selectedSetupInstanceIds).toEqual([setupActionCard.instanceId]);
    expect(drawn.instances.find((instance) => instance.instanceId === setupActionCard.instanceId)?.zoneId).toBe('other');

    const playing = acceptOpeningSetup(drawn);

    expect(getZoneInstances(playing, 'play').map((instance) => instance.instanceId)).toEqual([
      ...mana.map((instance) => instance.instanceId),
      setupActionCard.instanceId,
    ]);
    expect(playing.openingSetup.selectedSetupInstanceIds).toEqual([]);
  });

  test('deselecting a reserved card after mulligan returns it to library instead of the new hand', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const mana = getOpeningManaInstances(initial)[0];
    if (!mana) {
      throw new Error('expected mana card');
    }
    const reserved = drawOpeningHand(toggleOpeningManaSelection(initial, mana.instanceId, true));
    const afterMulligan = mulliganOpeningHand(reserved, noShuffle);

    const deselected = toggleOpeningManaSelection(afterMulligan, mana.instanceId, false);

    expect(deselected.openingSetup.selectedManaInstanceIds).toEqual([]);
    expect(deselected.instances.find((instance) => instance.instanceId === mana.instanceId)?.zoneId).toBe('library');
    expect(getZoneInstances(deselected, 'hand').some((instance) => instance.instanceId === mana.instanceId)).toBe(false);
    expect(getZoneInstances(deselected, 'hand')).toHaveLength(7);
  });

  test('opening hand size changes do not draw before hand step, then trim or refill the current hand', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);

    const resizedBeforeDraw = setOpeningHandSize(initial, 5);

    expect(resizedBeforeDraw.handSize).toBe(5);
    expect(getZoneInstances(resizedBeforeDraw, 'hand')).toHaveLength(0);
    expect(countZone(resizedBeforeDraw, 'library')).toBe(12);

    const smallerHand = drawOpeningHand(resizedBeforeDraw);

    expect(smallerHand.handSize).toBe(5);
    expect(getZoneInstances(smallerHand, 'hand')).toHaveLength(5);
    expect(countZone(smallerHand, 'library')).toBe(7);

    const largerHand = setOpeningHandSize(smallerHand, 8);

    expect(largerHand.handSize).toBe(8);
    expect(getZoneInstances(largerHand, 'hand')).toHaveLength(8);
    expect(countZone(largerHand, 'library')).toBe(4);
  });

  test('keep moves selected mana to board and saves setup snapshot', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const mana = getOpeningManaInstances(initial).slice(0, 3);
    const setup = getOpeningSetupInstances(initial)[0];
    if (mana.length !== 3 || !setup) {
      throw new Error('expected opening selections');
    }
    const reserved = drawOpeningHand(mana.reduce(
      (state, instance) => toggleOpeningManaSelection(state, instance.instanceId, true),
      initial,
    ));

    const playing = acceptOpeningSetup(reserved);

    expect(playing.phase).toBe('play');
    expect(playing.setupSnapshot).not.toBeNull();
    expect(getZoneInstances(playing, 'play').map((instance) => instance.instanceId)).toEqual(mana.map((instance) => instance.instanceId));
    expect(getZoneInstances(playing, 'play').map((instance) => [instance.boardX, instance.boardY])).toEqual([[12, 78], [20, 78], [28, 78]]);
    expect(playing.instances.find((instance) => instance.instanceId === setup.instanceId)?.zoneId).not.toBe('play');
    expect(getZoneInstances(playing, 'hand')).toHaveLength(7);
    expect(getZoneInstances(playing, 'hand').every((instance) => instance.setupOrigin === false)).toBe(true);
    expect(getZoneInstances(playing, 'play').every((instance) => instance.setupOrigin === true)).toBe(true);
    expect(playing.openingSetup.selectedManaInstanceIds).toEqual([]);
    expect(playing.openingSetup.selectedSetupInstanceIds).toEqual([]);
  });

  test('reset restores the accepted opening setup snapshot exactly', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const mana = getOpeningManaInstances(initial)[0];
    if (!mana) {
      throw new Error('expected mana card');
    }
    const playing = acceptOpeningSetup(drawOpeningHand(toggleOpeningManaSelection(initial, mana.instanceId, true)));
    const changed = drawCards(moveInstanceToZone(playing, getZoneInstances(playing, 'hand')[0]?.instanceId ?? '', 'discard'), 1);

    expect(resetToSetup(changed).instances).toEqual(playing.setupSnapshot?.instances);
  });

  test('detects stale drafts', () => {
    const deck = buildDeck();
    const draft = serializePlaytestDraft(createInitialPlaytestState(deck, noShuffle));

    expect(draft.version).toBe(2);
    expect(isStoredDraftStale(draft, deck)).toBe(false);
    expect(isStoredDraftStale(draft, { ...deck, updated_at: '2026-02-01T00:00:00Z' })).toBe(true);
  });

  test('flips one or multiple cards', () => {
    const initial = drawOpeningHand(createInitialPlaytestState(buildDeck(), noShuffle));
    const [first, second] = getZoneInstances(initial, 'hand');
    if (!first || !second) {
      throw new Error('expected hand cards');
    }

    const flippedOne = toggleCardFace(initial, first.instanceId);
    const flippedBoth = toggleCardsFace(flippedOne, [first.instanceId, second.instanceId]);

    expect(flippedOne.instances.find((instance) => instance.instanceId === first.instanceId)?.face).toBe('back');
    expect(flippedBoth.instances.find((instance) => instance.instanceId === first.instanceId)?.face).toBe('front');
    expect(flippedBoth.instances.find((instance) => instance.instanceId === second.instanceId)?.face).toBe('back');
  });

  test('clones cards with new ids and preserves face state', () => {
    const initial = drawOpeningHand(createInitialPlaytestState(buildDeck(), noShuffle));
    const [first, second] = getZoneInstances(initial, 'hand');
    if (!first || !second) {
      throw new Error('expected hand cards');
    }
    const flipped = toggleCardFace(initial, first.instanceId);

    const clonedHand = cloneCardInstance(flipped, first.instanceId);
    const handCopies = getZoneInstances(clonedHand, 'hand').filter((instance) => instance.cardId === first.cardId);
    const copiedHandCard = handCopies.find((instance) => instance.instanceId.includes(':copy:'));

    expect(copiedHandCard?.instanceId).not.toBe(first.instanceId);
    expect(copiedHandCard?.face).toBe('back');
    expect(copiedHandCard?.setupOrigin).toBe(false);

    const clonedBoard = cloneCardInstances(clonedHand, [first.instanceId, second.instanceId], {
      type: 'board',
      anchorX: 40,
      anchorY: 45,
    });
    const boardCopies = getZoneInstances(clonedBoard, 'play').filter((instance) => instance.instanceId.includes(':copy:'));

    expect(boardCopies).toHaveLength(2);
    expect(boardCopies.map((instance) => [instance.boardX, instance.boardY])).toEqual([[40, 45], [44, 49]]);
  });

  test('clones cards from snapshots after the source instance changes or is removed', () => {
    const initial = drawOpeningHand(createInitialPlaytestState(buildDeck(), noShuffle));
    const [first] = getZoneInstances(initial, 'hand');
    if (!first) {
      throw new Error('expected hand card');
    }

    const copiedBeforeFlip = { ...first };
    const sourceChanged = toggleCardFace(initial, first.instanceId);
    const sourceRemoved = deleteCardInstances(sourceChanged, [first.instanceId]);

    const pasted = cloneCardInstanceSnapshots(sourceRemoved, [copiedBeforeFlip], {
      type: 'board',
      anchorX: 42,
      anchorY: 46,
    });
    const pastedCopy = getZoneInstances(pasted, 'play').find((instance) => instance.cardId === first.cardId);

    expect(sourceRemoved.instances.some((instance) => instance.instanceId === first.instanceId)).toBe(false);
    expect(pastedCopy?.instanceId).not.toBe(first.instanceId);
    expect(pastedCopy?.face).toBe('front');
    expect(pastedCopy?.boardX).toBe(42);
    expect(pastedCopy?.boardY).toBe(46);
  });

  test('deletes card instances and normalizes remaining pile groups', () => {
    const initial = drawOpeningHand(createInitialPlaytestState(buildDeck(), noShuffle));
    const [first, second] = getZoneInstances(initial, 'hand');
    if (!first || !second) {
      throw new Error('expected hand cards');
    }
    const playing = acceptOpeningSetup(initial);
    const placed = placeInstanceOnBoard(
      placeInstanceOnBoard(playing, first.instanceId, 20, 30),
      second.instanceId,
      24,
      30,
    );
    const piled = addInstanceToVisualPile(placed, second.instanceId, first.instanceId);

    const deleted = deleteCardInstances(piled, [second.instanceId]);
    const remaining = deleted.instances.find((instance) => instance.instanceId === first.instanceId);

    expect(deleted.instances.some((instance) => instance.instanceId === second.instanceId)).toBe(false);
    expect(remaining?.pileGroupId).toBeNull();
    expect(remaining?.pileOrder).toBeNull();
    expect(countZone(deleted, 'play')).toBe(1);
  });

  test('shuffles a zone without moving cards between zones', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const libraryBefore = getZoneInstances(initial, 'library').map((instance) => instance.instanceId);

    const shuffled = shuffleZone(initial, 'library', noShuffle);
    const libraryAfter = getZoneInstances(shuffled, 'library').map((instance) => instance.instanceId);

    expect(libraryAfter).not.toEqual(libraryBefore);
    expect([...libraryAfter].sort()).toEqual([...libraryBefore].sort());
    expect(countZone(shuffled, 'hand')).toBe(countZone(initial, 'hand'));
    expect(countZone(shuffled, 'library')).toBe(countZone(initial, 'library'));
  });

  test('keeps one-card zone shuffles as no-ops', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const singleCardLibrary = getZoneInstances(initial, 'library')
      .slice(1)
      .reduce(
        (state, instance) => moveInstanceToZone(state, instance.instanceId, 'hand'),
        initial,
      );

    expect(countZone(singleCardLibrary, 'library')).toBe(1);
    expect(shuffleZone(singleCardLibrary, 'library', noShuffle)).toBe(singleCardLibrary);
  });

  test('creates and extends visual piles from card-level fields', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const [first, second, third] = getZoneInstances(initial, 'library');
    if (!first || !second || !third) {
      throw new Error('expected library cards');
    }
    const placed = [first, second, third].reduce(
      (state, instance, index) => placeInstanceOnBoard(state, instance.instanceId, 20 + index * 10, 30),
      initial,
    );

    const piled = addInstanceToVisualPile(placed, second.instanceId, first.instanceId);
    const extended = addInstanceToVisualPile(piled, third.instanceId, first.instanceId);
    const pileMembers = getZoneInstances(extended, 'play').filter((instance) => instance.pileGroupId);

    expect(new Set(pileMembers.map((instance) => instance.pileGroupId)).size).toBe(1);
    expect(pileMembers.map((instance) => instance.pileOrder)).toEqual([0, 1, 2]);
    expect(pileMembers.every((instance) => instance.boardX === 20)).toBe(true);
    expect(pileMembers.every((instance) => instance.boardY === 30)).toBe(true);
  });

  test('next turn draws one card and untaps board cards', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const playing = acceptOpeningSetup(drawOpeningHand(initial));
    const handCard = getZoneInstances(playing, 'hand')[0];
    if (!handCard) {
      throw new Error('expected hand card');
    }
    const tapped = toggleTapped(placeInstanceOnBoard(playing, handCard.instanceId, 25, 30), handCard.instanceId);

    const nextTurn = startNextTurn(tapped);

    expect(nextTurn.instances.find((instance) => instance.instanceId === handCard.instanceId)?.tapped).toBe(false);
    expect(countZone(nextTurn, 'hand')).toBe(countZone(tapped, 'hand') + 1);
    expect(countZone(nextTurn, 'library')).toBe(countZone(tapped, 'library') - 1);
  });

  test('removing a middle pile card preserves the rest and collapses single-card piles', () => {
    const initial = createInitialPlaytestState(buildDeck(), noShuffle);
    const [first, second, third] = getZoneInstances(initial, 'library');
    if (!first || !second || !third) {
      throw new Error('expected library cards');
    }
    const placed = [first, second, third].reduce(
      (state, instance, index) => placeInstanceOnBoard(state, instance.instanceId, 20 + index * 10, 30),
      initial,
    );
    const piled = addInstanceToVisualPile(addInstanceToVisualPile(placed, second.instanceId, first.instanceId), third.instanceId, first.instanceId);

    const withoutMiddle = removeInstanceFromVisualPile(piled, second.instanceId, 55, 60);
    const remainingPiled = getZoneInstances(withoutMiddle, 'play').filter((instance) => instance.pileGroupId);
    const removed = getZoneInstances(withoutMiddle, 'play').find((instance) => instance.instanceId === second.instanceId);

    expect(remainingPiled).toHaveLength(2);
    expect(removed?.pileGroupId).toBeNull();
    expect(removed?.boardX).toBe(55);
    expect(removed?.boardY).toBe(60);

    const collapsed = removeInstanceFromVisualPile(withoutMiddle, third.instanceId);

    expect(getZoneInstances(collapsed, 'play').every((instance) => instance.pileGroupId === null)).toBe(true);
  });
});
