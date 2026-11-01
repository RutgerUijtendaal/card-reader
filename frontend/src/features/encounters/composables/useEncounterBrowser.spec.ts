import { createApp, defineComponent, h, nextTick, ref } from 'vue';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import type { CardFaction } from '@/domain/cards/cardFactions';
import { useEncounterBrowser } from './useEncounterBrowser';
const api = vi.hoisted(() => ({ filters: vi.fn(), cards: vi.fn(), bosses: vi.fn() }));
vi.mock('@/domain/cards/api', () => ({ fetchCards: api.cards, fetchCardFilters: api.filters }));
vi.mock('@/domain/encounters/api', () => ({ fetchEncounterBosses: api.bosses }));
const cleanup: Array<() => void> = [];
beforeEach(() => {
  vi.useFakeTimers();
  vi.clearAllMocks();
  localStorage.clear();
  api.filters.mockResolvedValue({ keywords: [], tags: [], symbols: [], types: [] });
  const empty = {
    results: [],
    count: 0,
    page: 1,
    page_size: 30,
    next_page: null,
    previous_page: null,
  };
  api.cards.mockResolvedValue(empty);
  api.bosses.mockResolvedValue(empty);
});
afterEach(() => {
  cleanup.splice(0).forEach((fn) => fn());
  vi.useRealTimers();
});
const mount = async () => {
  const mode = ref<'boss' | 'details' | 'cards'>('cards');
  const factions = ref<CardFaction[]>([]);
  const cardIds = ref<string[]>([]);
  let browser!: ReturnType<typeof useEncounterBrowser>;
  const component = defineComponent({
    setup() {
      browser = useEncounterBrowser({ mode, bossFactions: factions, cardIds });
      return () => h('div');
    },
  });
  const target = document.createElement('div');
  document.body.appendChild(target);
  const app = createApp(component);
  app.mount(target);
  cleanup.push(() => {
    app.unmount();
    target.remove();
  });
  await nextTick();
  await vi.advanceTimersByTimeAsync(0);
  return { browser, mode, factions, cardIds };
};
test('uses the shared filter catalog and collection with explicit Evil scope in both modes', async () => {
  const { browser, mode, cardIds } = await mount();
  expect(api.filters).toHaveBeenCalledWith('evil');
  expect(api.cards.mock.calls[0][0].get('card_pool')).toBe('evil');
  browser.filters.setCurrentDeckOnly(true);
  cardIds.value = ['a', 'b'];
  expect(browser.buildSearchParams().getAll('card_ids')).toEqual(['a', 'b']);
  mode.value = 'boss';
  await nextTick();
  await vi.advanceTimersByTimeAsync(250);
  const params = api.bosses.mock.calls.at(-1)![0] as URLSearchParams;
  expect(params.get('card_pool')).toBe('evil');
  expect(params.get('card_roles')).toBe('boss');
  expect(params.getAll('card_ids')).toEqual([]);
  expect(params.get('show_groups')).toBe('true');
});
test('boss presets clear only faction exclusions and preserve search, sorting and other filters', async () => {
  const { browser, factions, mode } = await mount();
  browser.filters.applyRouteFilterState({
    ...browser.filters.readFilterState(),
    query: 'guard',
    cardFactionKeys: ['fire'],
    cardFactionExcludeKeys: ['blood'],
    cardFactionMatch: 'all',
    attackMin: '5',
  });
  browser.filters.setSortOverride('name_asc');
  factions.value = ['order', 'blood'];
  await nextTick();
  const state = browser.filters.readFilterState();
  expect(new Set(state.cardFactionKeys)).toEqual(new Set(['order', 'blood']));
  expect(state.cardFactionExcludeKeys).toEqual([]);
  expect(state.cardFactionMatch).toBe('any');
  expect(state.query).toBe('guard');
  expect(state.attackMin).toBe('5');
  expect(browser.buildSearchParams().get('sort')).toBe('name_asc');
  browser.filters.filterSectionsState.value.onUpdateSelectedCardFactions(['dark']);
  mode.value = 'details';
  await nextTick();
  mode.value = 'cards';
  await nextTick();
  expect(browser.filters.readFilterState().cardFactionKeys).toEqual(['dark']);
  factions.value = [];
  await nextTick();
  expect(browser.filters.readFilterState().cardFactionKeys).toEqual([]);
  expect(browser.filters.query.value).toBe('guard');
});

test('picking a boss neither filters nor reloads the boss gallery, and presets Cards on leaving it', async () => {
  const { browser, factions, mode } = await mount();
  mode.value = 'boss';
  await nextTick();
  await vi.advanceTimersByTimeAsync(250);
  api.bosses.mockClear();
  for (const picked of [['order'], ['blood', 'dark'], ['order']] as CardFaction[][]) {
    factions.value = picked;
    await nextTick();
    await vi.advanceTimersByTimeAsync(250);
  }
  expect(api.bosses).not.toHaveBeenCalled();
  expect(browser.filters.readFilterState().cardFactionKeys).toEqual([]);
  mode.value = 'cards';
  await nextTick();
  expect(browser.filters.readFilterState().cardFactionKeys).toEqual(['order']);
});

test('editing deck contents preserves loaded gallery pages when Current Encounter Only is off', async () => {
  api.cards.mockResolvedValueOnce({
    results: [{ id: 'first', result_type: 'card' }],
    count: 2,
    page: 1,
    page_size: 1,
    next_page: 2,
    previous_page: null,
  });
  const { browser, cardIds } = await mount();
  api.cards.mockResolvedValueOnce({
    results: [{ id: 'second', result_type: 'card' }],
    count: 2,
    page: 2,
    page_size: 1,
    next_page: null,
    previous_page: 1,
  });
  await browser.gallery.loadNextPage();
  const loadedCards = browser.gallery.galleryCards.value;
  expect(loadedCards.map((card) => card.id)).toEqual(['first', 'second']);
  for (const ids of [['first'], ['first', 'second'], ['second', 'first'], []]) {
    cardIds.value = ids;
    await nextTick();
    await vi.advanceTimersByTimeAsync(250);
  }
  expect(api.cards).toHaveBeenCalledTimes(2);
  expect(browser.gallery.galleryCards.value).toBe(loadedCards);
  expect(browser.gallery.nextPage.value).toBeNull();
});

test('Current Encounter Only refreshes for membership changes, but not ordering or quantity-only snapshots', async () => {
  const { browser, cardIds, mode } = await mount();
  cardIds.value = ['a', 'b'];
  browser.filters.setCurrentDeckOnly(true);
  await nextTick();
  await vi.advanceTimersByTimeAsync(250);
  api.cards.mockClear();
  for (const ids of [
    ['a', 'b'],
    ['b', 'a'],
    ['a', 'a', 'b'],
  ]) {
    cardIds.value = ids;
    await nextTick();
    await vi.advanceTimersByTimeAsync(250);
  }
  expect(api.cards).not.toHaveBeenCalled();
  cardIds.value = ['b'];
  await nextTick();
  await vi.advanceTimersByTimeAsync(250);
  expect(api.cards).toHaveBeenCalledTimes(1);
  expect(api.cards.mock.calls[0][0].getAll('card_ids')).toEqual(['b']);
  mode.value = 'boss';
  await nextTick();
  await vi.advanceTimersByTimeAsync(250);
  api.bosses.mockClear();
  cardIds.value = ['c'];
  await nextTick();
  await vi.advanceTimersByTimeAsync(250);
  expect(api.bosses).not.toHaveBeenCalled();
});
