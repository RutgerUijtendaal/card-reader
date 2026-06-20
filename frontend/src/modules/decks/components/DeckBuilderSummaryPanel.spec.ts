/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick, ref } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import DeckBuilderSummaryPanel from '@/modules/decks/components/DeckBuilderSummaryPanel.vue';

const sortableMock = vi.hoisted(() => ({
  latestOptions: null as null | {
    scroll?: boolean | HTMLElement;
    forceAutoScrollFallback?: boolean;
    bubbleScroll?: boolean;
    scrollSensitivity?: number;
    scrollSpeed?: number;
    onStart?: () => void;
    onEnd?: () => void;
    onUpdate?: (event: { item: HTMLElement; newIndex?: number }) => void;
  },
  option: vi.fn(),
}));

vi.mock('@vueuse/integrations/useSortable', () => ({
  useSortable: vi.fn((_element, _list, options) => {
    sortableMock.latestOptions = options;
    return {
      option: sortableMock.option,
      start: vi.fn(),
      stop: vi.fn(),
    };
  }),
}));

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
      sortableCardId: { type: String, required: true },
    },
    setup(props) {
      return () => {
        const cardId = (props.entry as { card: { id: string } }).card.id;
        return h('div', {
          'data-testid': `row-${cardId}`,
          'data-card-id': props.sortableCardId,
        });
      };
    },
  }),
}));

vi.mock('@/components/modals/ConfirmModal.vue', () => ({
  default: defineComponent({
    props: {
      open: { type: Boolean, required: true },
      title: { type: String, required: true },
      message: { type: String, required: true },
    },
    emits: ['confirm', 'cancel'],
    setup(props, { emit }) {
      return () =>
        props.open
          ? h('div', { 'data-testid': 'confirm-modal' }, [
            h('div', props.title),
            h('div', props.message),
            h('button', { onClick: () => emit('confirm') }, 'Confirm'),
            h('button', { onClick: () => emit('cancel') }, 'Cancel'),
          ])
          : null;
    },
  }),
}));

vi.mock('@/components/cards/CardLoadingSkeleton.vue', () => ({
  default: defineComponent({
    props: {
      animated: { type: Boolean, default: true },
    },
    setup(props) {
      return () => h('div', { 'data-testid': 'card-loading-skeleton', 'data-animated': String(props.animated) });
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
  const selectedHero = ref<{
    id: string;
    name: string;
    label: string;
    image_url: string;
  } | null>({
    id: 'hero-1',
    name: 'Aurora Hero',
    label: 'Hero',
    image_url: '/hero.png',
  });
  const mainboardEntries = ref([
    { card: { id: 'card-1' }, quantity: 3 },
    { card: { id: 'card-3' }, quantity: 1 },
  ]);
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
      lastBoardEntryChange: ref(null),
      form: {
        name: 'Aurora Tempo',
        description: '',
        visibility: 'private',
      },
      selectedHero,
      validationMessages: ref<string[]>([]),
      warningMessages: ref<string[]>([]),
      blockingMessages: ref<string[]>([]),
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
      getCardQuantityLimit: vi.fn(() => 4),
      getBoardMoveDestinations: vi.fn(() => []),
      moveEntryToBoard: vi.fn(),
      reorderEntries: vi.fn(),
      moveEntryWithinBoard: vi.fn(),
      moveEntryToIndex: vi.fn(),
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

const showSideboardActionsTrigger = async (container: HTMLElement): Promise<HTMLButtonElement> => {
  const sideboardPill = Array.from(container.querySelectorAll('button')).find((button) =>
    (button.textContent ?? '').includes('Flex (2)'),
  );
  if (!(sideboardPill instanceof HTMLButtonElement)) {
    throw new Error('expected sideboard pill');
  }

  sideboardPill.parentElement?.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
  await nextTick();

  const sideboardActionsButton = container.querySelector<HTMLButtonElement>('[aria-label="Open sideboard actions for Flex"]');
  if (!(sideboardActionsButton instanceof HTMLButtonElement)) {
    throw new Error('expected sideboard actions button');
  }

  return sideboardActionsButton;
};

describe('DeckBuilderSummaryPanel', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
    sortableMock.latestOptions = null;
    sortableMock.option.mockClear();
  });

  test('renders a compact hero header and keeps details collapsed by default', async () => {
    const mounted = await mountPanel();
    const text = mounted.container.textContent ?? '';
    const topSection = mounted.container.querySelector('[data-testid="deck-summary-top"]');
    const listSection = mounted.container.querySelector('[data-testid="deck-summary-list"]');

    expect(text).toContain('Aurora Tempo');
    expect(text).toContain('Aurora Hero');
    expect(topSection).not.toBeNull();
    expect(listSection).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="mana-curve"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="deck-summary-hero-details"]')).toBeNull();

    mounted.unmount();
  });

  test('setup mode places selected hero before deck properties without an extra image frame', async () => {
    const mounted = await mountPanel();
    mounted.controller.deck.isSetupStep.value = true;
    await nextTick();

    const text = mounted.container.textContent ?? '';
    const heroIndex = text.indexOf('Selected Hero');
    const nameIndex = text.indexOf('Name');
    const heroImage = mounted.container.querySelector<HTMLImageElement>('img[alt="Aurora Hero"]');

    expect(heroIndex).toBeGreaterThanOrEqual(0);
    expect(nameIndex).toBeGreaterThanOrEqual(0);
    expect(heroIndex).toBeLessThan(nameIndex);
    expect(heroImage).not.toBeNull();
    expect(heroImage?.className).not.toContain('theme-card-frame');
    expect(heroImage?.parentElement?.className).toContain('aspect-[63/88]');
    expect(text).not.toContain('Aurora Hero');

    mounted.unmount();
  });

  test('setup mode renders a static card placeholder when no hero is selected', async () => {
    const mounted = await mountPanel();
    mounted.controller.deck.isSetupStep.value = true;
    mounted.controller.deck.selectedHero.value = null;
    await nextTick();

    const placeholder = mounted.container.querySelector('.theme-card-frame');
    const skeleton = mounted.container.querySelector('[data-testid="card-loading-skeleton"]');

    expect(placeholder).not.toBeNull();
    expect(placeholder?.className).toContain('aspect-[63/88]');
    expect(skeleton).not.toBeNull();
    expect(skeleton?.getAttribute('data-animated')).toBe('false');

    mounted.unmount();
  });

  test('setup mode shows setup issues below the hero area', async () => {
    const mounted = await mountPanel();
    mounted.controller.deck.isSetupStep.value = true;
    mounted.controller.deck.setupMessages.value = ['Deck name is required.'];
    await nextTick();

    const text = mounted.container.textContent ?? '';
    expect(text).not.toContain('A hero card is required.');
    expect(text.indexOf('Setup Issues')).toBeGreaterThan(text.indexOf('Selected Hero'));
    expect(text.indexOf('Setup Issues')).toBeLessThan(text.indexOf('Name'));

    mounted.unmount();
  });

  test('setup mode marks deck name required and disables continue without a name', async () => {
    const mounted = await mountPanel();
    mounted.controller.deck.isSetupStep.value = true;
    mounted.controller.deck.form.name = '';
    await nextTick();

    const continueButton = Array.from(mounted.container.querySelectorAll<HTMLButtonElement>('button')).find(
      (button) => button.textContent?.trim() === 'Continue',
    );

    expect(mounted.container.textContent).toContain('Name *');
    expect(mounted.container.textContent).not.toContain('Deck name is required.');
    expect(continueButton?.disabled).toBe(true);

    mounted.unmount();
  });

  test('focuses the deck name after selecting a hero during setup', async () => {
    const mounted = await mountPanel();
    mounted.controller.deck.isSetupStep.value = true;
    mounted.controller.deck.selectedHero.value = null;
    await nextTick();

    mounted.controller.deck.selectedHero.value = {
      id: 'hero-2',
      name: 'Borealis Hero',
      label: 'Hero',
      image_url: '/hero-2.png',
    };
    await nextTick();
    await nextTick();

    expect(document.activeElement).toBe(
      mounted.container.querySelector<HTMLInputElement>('input[placeholder="Deck name"]'),
    );

    mounted.unmount();
  });

  test('uses enter in the setup deck name field to continue when setup is complete', async () => {
    const mounted = await mountPanel();
    mounted.controller.deck.isSetupStep.value = true;
    mounted.controller.deck.form.name = 'Aurora Tempo';
    await nextTick();

    const nameInput = mounted.container.querySelector<HTMLInputElement>('input[placeholder="Deck name"]');
    if (!(nameInput instanceof HTMLInputElement)) {
      throw new Error('expected deck name input');
    }

    nameInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    await nextTick();

    expect(mounted.controller.lockSetup).toHaveBeenCalledTimes(1);

    mounted.unmount();
  });

  test('does not duplicate validation messages in the build sidebar', async () => {
    const mounted = await mountPanel();
    mounted.controller.deck.validationMessages.value = ['Deck must contain at least 20 mainboard cards.'];
    mounted.controller.deck.warningMessages.value = ['Legendary cards are limited to 1 copy per deck.'];
    await nextTick();

    const text = mounted.container.textContent ?? '';
    expect(text).not.toContain('Validation');
    expect(text).not.toContain('Deck must contain at least 20 mainboard cards.');
    expect(text).not.toContain('Legendary cards are limited to 1 copy per deck.');

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

    const heroDetails = document.body.querySelector<HTMLElement>('[data-testid="deck-summary-hero-details"]');
    const manaCurve = heroDetails?.querySelector('[data-testid="mana-curve"]');
    expect(manaCurve?.getAttribute('data-compact')).toBe('true');
    expect(heroDetails?.style.position).toBe('fixed');
    expect(heroDetails?.textContent ?? '').not.toContain('Aurora Hero');

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

  test('commits sortable updates to the deck draft', async () => {
    const mounted = await mountPanel();
    const firstRow = mounted.container.querySelector<HTMLElement>('[data-testid="row-card-1"]');
    if (!firstRow) {
      throw new Error('expected board rows');
    }

    sortableMock.latestOptions?.onUpdate?.({
      item: firstRow,
      newIndex: 1,
    });
    await nextTick();

    expect(mounted.controller.deck.moveEntryToIndex).toHaveBeenCalledWith(
      'mainboard',
      'card-1',
      1,
    );

    mounted.unmount();
  });

  test('shows sideboard actions trigger only for sideboards and opening it does not select the board', async () => {
    const mounted = await mountPanel();
    const sideboardActionsButton = await showSideboardActionsTrigger(mounted.container);

    expect(sideboardActionsButton).not.toBeNull();
    expect(mounted.container.querySelector('[aria-label="Open sideboard actions for Mainboard"]')).toBeNull();

    sideboardActionsButton?.click();
    await nextTick();

    expect(mounted.controller.deck.selectBoard).not.toHaveBeenCalledWith('side-1');
    expect(document.body.textContent ?? '').toContain('Rename');
    expect(document.body.textContent ?? '').toContain('Delete');

    mounted.unmount();
  });

  test('pins drag autoscroll to the summary list instead of bubbling to the page', async () => {
    const mounted = await mountPanel();
    const summaryList = mounted.container.querySelector<HTMLElement>('[data-testid="deck-summary-list"]');

    expect(summaryList).not.toBeNull();
    expect(summaryList?.classList.contains('overscroll-contain')).toBe(true);
    expect(sortableMock.latestOptions?.scroll).toBe(true);
    expect(sortableMock.latestOptions?.forceAutoScrollFallback).toBe(true);
    expect(sortableMock.latestOptions?.bubbleScroll).toBe(false);
    expect(sortableMock.latestOptions?.scrollSensitivity).toBe(180);
    expect(sortableMock.latestOptions?.scrollSpeed).toBe(18);
    expect(sortableMock.option).toHaveBeenCalledWith('scroll', summaryList);
    expect(sortableMock.option).toHaveBeenCalledWith('bubbleScroll', false);

    sortableMock.latestOptions?.onStart?.();
    sortableMock.latestOptions?.onEnd?.();

    expect(sortableMock.option).toHaveBeenCalledWith('scroll', summaryList);
    expect(sortableMock.option).toHaveBeenCalledWith('bubbleScroll', false);

    mounted.unmount();
  });

  test('rename from the sideboard actions menu enters inline edit mode and saves on enter', async () => {
    const mounted = await mountPanel();
    const sideboardActionsButton = await showSideboardActionsTrigger(mounted.container);
    sideboardActionsButton?.click();
    await nextTick();

    const renameButton = Array.from(document.body.querySelectorAll<HTMLButtonElement>('button')).find((button) =>
      (button.textContent ?? '').includes('Rename'),
    );
    renameButton?.click();
    await nextTick();

    const renameInput = mounted.container.querySelector<HTMLInputElement>('[aria-label="Rename Flex"]');
    expect(renameInput).not.toBeNull();

    if (!(renameInput instanceof HTMLInputElement)) {
      throw new Error('expected rename input');
    }

    renameInput.value = 'Control';
    renameInput.dispatchEvent(new Event('input', { bubbles: true }));
    renameInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    await nextTick();

    expect(mounted.controller.deck.renameSideboard).toHaveBeenCalledWith('side-1', 'Control');

    mounted.unmount();
  });

  test('rename from the sideboard actions menu cancels on escape', async () => {
    const mounted = await mountPanel();
    const sideboardActionsButton = await showSideboardActionsTrigger(mounted.container);
    sideboardActionsButton?.click();
    await nextTick();

    const renameButton = Array.from(document.body.querySelectorAll<HTMLButtonElement>('button')).find((button) =>
      (button.textContent ?? '').includes('Rename'),
    );
    renameButton?.click();
    await nextTick();

    const renameInput = mounted.container.querySelector<HTMLInputElement>('[aria-label="Rename Flex"]');
    if (!(renameInput instanceof HTMLInputElement)) {
      throw new Error('expected rename input');
    }

    renameInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await nextTick();

    expect(mounted.controller.deck.renameSideboard).not.toHaveBeenCalled();
    expect(mounted.container.querySelector('[aria-label="Rename Flex"]')).toBeNull();

    mounted.unmount();
  });

  test('delete from the sideboard actions menu requires confirmation and falls back to mainboard for the active sideboard', async () => {
    const mounted = await mountPanel();
    const sideboardButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      (button.textContent ?? '').includes('Flex'),
    );
    sideboardButton?.click();
    await nextTick();

    const sideboardActionsButton = await showSideboardActionsTrigger(mounted.container);
    sideboardActionsButton?.click();
    await nextTick();

    const deleteButton = Array.from(document.body.querySelectorAll<HTMLButtonElement>('button')).find((button) =>
      (button.textContent ?? '').includes('Delete'),
    );
    deleteButton?.click();
    await nextTick();

    expect(mounted.controller.deck.removeSideboard).not.toHaveBeenCalled();
    expect(document.body.textContent ?? '').toContain("Delete sideboard 'Flex'?");

    const confirmButton = Array.from(document.body.querySelectorAll<HTMLButtonElement>('button')).find((button) =>
      (button.textContent ?? '') === 'Confirm',
    );
    confirmButton?.click();
    await nextTick();

    expect(mounted.controller.deck.selectBoard).toHaveBeenLastCalledWith('mainboard');
    expect(mounted.controller.deck.removeSideboard).toHaveBeenCalledWith('side-1');

    mounted.unmount();
  });
});
