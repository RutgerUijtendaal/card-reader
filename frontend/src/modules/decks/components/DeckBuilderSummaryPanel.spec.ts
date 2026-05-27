/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick, ref } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import DeckBuilderSummaryPanel from '@/modules/decks/components/DeckBuilderSummaryPanel.vue';

vi.mock('@/api/client', () => ({
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('@/modules/decks/components/DeckManaCurve.vue', () => ({
  default: defineComponent({
    props: {
      title: { type: String, default: 'Mana Curve' },
      compact: { type: Boolean, default: false },
    },
    setup(props) {
      return () => h('div', { 'data-testid': 'mana-curve', 'data-compact': String(props.compact) }, props.title);
    },
  }),
}));

vi.mock('@/modules/decks/components/DeckBuilderBoardEntryRow.vue', () => ({
  default: defineComponent({
    props: {
      entry: { type: Object, required: true },
    },
    setup(props) {
      return () => h('div', { 'data-testid': `row-${(props.entry as { card: { id: string } }).card.id}` }, 'row');
    },
  }),
}));

const buildController = () => {
  const activeBoardId = ref('mainboard');
  const sideboards = ref([
    {
      id: 'side-1',
      name: 'Flex',
      entries: [{ card_id: 'card-2', quantity: 2 }],
    },
  ]);
  const selectedHero = ref({
    id: 'hero-1',
    name: 'Aurora Hero',
    label: 'Hero',
    image_url: '/hero.png',
  });
  const mainboardEntries = ref([{ card: { id: 'card-1' }, quantity: 3 }]);
  const activeSideboard = () => sideboards.value.find((sideboard) => sideboard.id === activeBoardId.value) ?? null;

  const controller = {
    filters: {
      hoverMode: ref('details'),
    },
    setBuilderStep: vi.fn(),
    lockSetup: vi.fn(),
    loading: ref(false),
    saving: ref(false),
    deckId: ref('deck-1'),
    backLink: ref('/my/decks'),
    backLabel: ref('Back'),
    deck: {
      isSetupStep: ref(false),
      form: {
        name: 'Aurora Tempo',
        description: '',
        visibility: 'private',
      },
      selectedHero,
      validationMessages: ref<string[]>([]),
      detailedMainboardEntries: ref(mainboardEntries.value),
      detailedActiveBoardEntries: ref(mainboardEntries.value),
      activeBoardId,
      totalMainboardCards: ref(30),
      totalMainboardManaTypeCards: ref(10),
      overallUniqueCards: ref(18),
      overallTotalCards: ref(30),
      deckStatusLabel: ref('Ready'),
      sideboardTabs: ref([
        {
          id: 'side-1',
          name: 'Flex',
          totalCards: 2,
          uniqueCards: 1,
        },
      ]),
      activeSideboard: ref(activeSideboard()),
      addSideboard: vi.fn(),
      selectBoard: vi.fn((boardId: string) => {
        activeBoardId.value = boardId;
        controller.deck.activeSideboard.value = activeSideboard();
        controller.deck.detailedActiveBoardEntries.value =
          boardId === 'mainboard' ? mainboardEntries.value : [{ card: { id: 'card-2' }, quantity: 2 }];
      }),
      renameSideboard: vi.fn(),
      removeSideboard: vi.fn(),
      boardRowActionDisabled: vi.fn(() => false),
      boardRowSecondaryActionDisabled: vi.fn(() => false),
      getBoardMoveDestinations: vi.fn(() => []),
      moveEntryToBoard: vi.fn(),
      changeQuantity: vi.fn(),
      removeEntry: vi.fn(),
      handleBoardRowAction: vi.fn(),
      handleBoardRowSecondaryAction: vi.fn(),
      setupMessages: ref<string[]>([]),
      setDeckName: vi.fn(),
      setDeckDescription: vi.fn(),
      setDeckVisibility: vi.fn(),
    },
  };

  return controller;
};

const mountPanel = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const controller = buildController();
  const app = createApp(DeckBuilderSummaryPanel, {
    controller,
  });
  app.mount(container);
  await nextTick();

  return {
    container,
    controller,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('DeckBuilderSummaryPanel', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  test('renders a compact hero header and keeps details collapsed by default', async () => {
    const mounted = await mountPanel();
    const text = mounted.container.textContent ?? '';

    expect(text).toContain('Aurora Tempo');
    expect(text).toContain('Aurora Hero');
    expect(mounted.container.querySelector('[data-testid="mana-curve"]')).toBeNull();

    mounted.unmount();
  });

  test('expands hero details and compact mana curve on toggle', async () => {
    const mounted = await mountPanel();
    const buttons = mounted.container.querySelectorAll('button');
    const heroToggle = Array.from(buttons).find((button) => (button.textContent ?? '').includes('Aurora Tempo'));
    if (!(heroToggle instanceof HTMLButtonElement)) {
      throw new Error('expected hero toggle');
    }

    heroToggle.click();
    await nextTick();

    const manaCurve = mounted.container.querySelector('[data-testid="mana-curve"]');
    expect(manaCurve?.getAttribute('data-compact')).toBe('true');
    expect(mounted.container.textContent ?? '').toContain('Mainboard Curve');

    mounted.unmount();
  });

  test('keeps sideboards tabbed and switches rows by active board', async () => {
    const mounted = await mountPanel();
    const sideboardButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      (button.textContent ?? '').includes('Flex'),
    );
    if (!(sideboardButton instanceof HTMLButtonElement)) {
      throw new Error('expected sideboard button');
    }

    sideboardButton.click();
    await nextTick();

    expect(mounted.controller.deck.selectBoard).toHaveBeenCalledWith('side-1');
    expect(mounted.container.querySelector('[data-testid="row-card-2"]')).not.toBeNull();

    mounted.unmount();
  });
});
