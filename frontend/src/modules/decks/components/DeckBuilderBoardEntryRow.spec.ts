/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import type { DeckBoardMoveDestination } from '@/modules/decks/composables/useDeckEditorDraft';
import type { DeckEntrySummary } from '@/modules/decks/types';
import DeckBuilderBoardEntryRow from '@/modules/decks/components/DeckBuilderBoardEntryRow.vue';

vi.mock('@/components/cards/CardHoverTooltip.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('div', 'tooltip');
    },
  }),
}));

vi.mock('@/api/client', () => ({
  toAbsoluteApiUrl: (url: string) => url,
}));

const buildEntry = (quantity = 3): DeckEntrySummary => ({
  card: {
    id: 'card-1',
    key: 'card-1',
    label: 'Card 1',
    result_type: 'card',
    is_hero: false,
    template_id: 'template-1',
    version_id: 'version-1',
    version_number: 1,
    previous_version_id: null,
    is_latest: true,
    name: 'Card 1',
    mana_cost: '1',
    mana_symbols: [],
    mana_value: 1,
    attack: null,
    health: null,
    type_line: 'Item',
    rules_text: '',
    confidence: 1,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    image_url: '/card.png',
    keywords: [],
    tags: [],
    symbols: [],
    types: [],
  },
  quantity,
});

const buildZeroManaEntry = (quantity = 3): DeckEntrySummary => ({
  ...buildEntry(quantity),
  card: {
    ...buildEntry(quantity).card,
    mana_cost: '0',
    mana_value: 0,
  },
});

const buildMoveDestinations = (): DeckBoardMoveDestination[] => [
  {
    boardId: 'mainboard',
    label: 'Mainboard',
    disabled: false,
  },
  {
    boardId: 'sideboard-2',
    label: 'Flex Board',
    description: 'Sideboard copy limit is 100.',
    disabled: true,
  },
];

const buildSingleMoveDestination = (): DeckBoardMoveDestination[] => [
  {
    boardId: 'mainboard',
    label: 'Mainboard',
    disabled: false,
  },
];

const mountRow = async ({
  entry = buildEntry(),
  moveDestinations = [] as DeckBoardMoveDestination[],
  rowSecondaryActionDisabled = false,
}: {
  entry?: DeckEntrySummary;
  moveDestinations?: DeckBoardMoveDestination[];
  rowSecondaryActionDisabled?: boolean;
} = {}) => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const events: string[] = [];
  const app = createApp(DeckBuilderBoardEntryRow, {
    entry,
    hoverMode: 'details',
    moveDestinations,
    rowSecondaryActionDisabled,
    onRowAction: (cardId: string) => events.push(`row:${cardId}`),
    onRowSecondaryAction: (cardId: string) => events.push(`row-secondary:${cardId}`),
    onIncrement: (cardId: string) => events.push(`increment:${cardId}`),
    onDecrement: (cardId: string) => events.push(`decrement:${cardId}`),
    onRemove: (cardId: string) => events.push(`remove:${cardId}`),
    onMoveToBoard: (cardId: string, destinationBoardId: string) => events.push(`move:${cardId}:${destinationBoardId}`),
  });
  app.mount(container);
  await nextTick();

  return {
    container,
    events,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

const showRowControls = async (container: HTMLElement): Promise<void> => {
  const row = container.firstElementChild;
  if (!(row instanceof HTMLElement)) {
    throw new Error('expected row root');
  }

  row.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
  await nextTick();
};

describe('DeckBuilderBoardEntryRow', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('renders the hover quantity controls as one grouped cluster', async () => {
    const mounted = await mountRow();
    await showRowControls(mounted.container);

    const decrementButton = mounted.container.querySelector('[aria-label="Remove one copy"]');
    const incrementButton = mounted.container.querySelector('[aria-label="Add one copy"]');
    const controlGroup = decrementButton?.closest('.theme-card-frame-muted');
    const quantityBadge = mounted.container.querySelector('[data-testid="row-quantity-badge"]');

    expect(controlGroup).not.toBeNull();
    expect(controlGroup?.contains(incrementButton ?? null)).toBe(true);
    expect(controlGroup?.textContent).not.toContain('3');
    expect(quantityBadge?.textContent).toContain('x3');
    expect(mounted.container.querySelector('input')).toBeNull();

    mounted.unmount();
  });

  test('renders a persistent quantity badge, resting mana area, and an art strip when card imagery exists', async () => {
    const mounted = await mountRow({ entry: buildEntry(7) });

    expect(mounted.container.querySelector('[data-testid="row-quantity-badge"]')?.textContent).toContain('x7');
    expect(mounted.container.querySelector('[data-testid="row-mana-symbols"]')?.textContent).toContain('1');
    expect(mounted.container.textContent).toContain('Card 1');
    expect(mounted.container.querySelector('img[alt="Card 1"]')).not.toBeNull();

    mounted.unmount();
  });

  test('does not render a mana row for zero-cost cards', async () => {
    const mounted = await mountRow({ entry: buildZeroManaEntry() });

    expect(mounted.container.querySelector('[data-testid="row-mana-symbols"]')).toBeNull();
    expect(mounted.container.textContent).toContain('Card 1');

    mounted.unmount();
  });

  test('hides the move button when there are no other boards', async () => {
    const mounted = await mountRow();

    expect(mounted.container.querySelector('[aria-label="Move card to another board"]')).toBeNull();

    mounted.unmount();
  });

  test('shows the move button and lists only other boards', async () => {
    const mounted = await mountRow({ moveDestinations: buildMoveDestinations() });
    await showRowControls(mounted.container);
    const moveButton = mounted.container.querySelector<HTMLButtonElement>('[aria-label="Move card to another board"]');
    if (!(moveButton instanceof HTMLButtonElement)) {
      throw new Error('expected move button');
    }

    moveButton.click();
    await nextTick();

    const panels = Array.from(document.body.querySelectorAll<HTMLElement>('.theme-popover'));
    const moveMenuPanel = panels[panels.length - 1];
    const moveMenu = moveMenuPanel?.textContent ?? '';
    expect(moveMenu).toContain('Move To Board');
    expect(moveMenu).toContain('Mainboard');
    expect(moveMenu).toContain('Flex Board');
    expect(moveMenu).not.toContain('Card 1');

    mounted.unmount();
  });

  test('uses the move button as a direct swap when only one destination exists', async () => {
    const mounted = await mountRow({ moveDestinations: buildSingleMoveDestination() });
    await showRowControls(mounted.container);
    const moveButton = mounted.container.querySelector<HTMLButtonElement>('[aria-label="Move card to another board"]');
    if (!(moveButton instanceof HTMLButtonElement)) {
      throw new Error('expected move button');
    }

    moveButton.click();
    await nextTick();

    expect(mounted.events).toEqual(['move:card-1:mainboard']);
    expect(document.body.textContent ?? '').not.toContain('Move To Board');

    mounted.unmount();
  });

  test('move menu emits the destination board and closes', async () => {
    const mounted = await mountRow({ moveDestinations: buildMoveDestinations() });
    await showRowControls(mounted.container);
    const moveButton = mounted.container.querySelector<HTMLButtonElement>('[aria-label="Move card to another board"]');
    if (!(moveButton instanceof HTMLButtonElement)) {
      throw new Error('expected move button');
    }

    moveButton.click();
    await nextTick();

    const destinationButton = Array.from(document.body.querySelectorAll<HTMLButtonElement>('button')).find(
      (button) => button.textContent?.includes('Mainboard'),
    );
    if (!(destinationButton instanceof HTMLButtonElement)) {
      throw new Error('expected destination button');
    }

    destinationButton.click();
    await nextTick();

    expect(mounted.events).toEqual(['move:card-1:mainboard']);
    expect(document.body.textContent ?? '').not.toContain('Move To Board');

    mounted.unmount();
  });

  test('trash glyph still emits remove', async () => {
    const mounted = await mountRow();
    await showRowControls(mounted.container);
    const removeButton = mounted.container.querySelector<HTMLButtonElement>('[aria-label="Remove card from board"]');
    if (!(removeButton instanceof HTMLButtonElement)) {
      throw new Error('expected remove button');
    }

    removeButton.click();
    await nextTick();

    expect(mounted.events).toEqual(['remove:card-1']);

    mounted.unmount();
  });

  test('nested controls do not trigger row-level actions', async () => {
    const mounted = await mountRow({ moveDestinations: buildMoveDestinations() });
    await showRowControls(mounted.container);
    const decrementButton = mounted.container.querySelector<HTMLButtonElement>('[aria-label="Remove one copy"]');
    const incrementButton = mounted.container.querySelector<HTMLButtonElement>('[aria-label="Add one copy"]');
    const moveButton = mounted.container.querySelector<HTMLButtonElement>('[aria-label="Move card to another board"]');
    const removeButton = mounted.container.querySelector<HTMLButtonElement>('[aria-label="Remove card from board"]');

    decrementButton?.click();
    incrementButton?.click();
    moveButton?.click();
    removeButton?.click();
    await nextTick();

    expect(mounted.events).toEqual(['decrement:card-1', 'increment:card-1', 'remove:card-1']);

    mounted.unmount();
  });

  test('hides heavy row controls until hover or focus state reveals them', async () => {
    const mounted = await mountRow({ moveDestinations: buildMoveDestinations() });

    const countControls = mounted.container.querySelector('[data-testid="row-count-controls"]');
    const manaSymbols = mounted.container.querySelector('[data-testid="row-mana-symbols"]');
    const moveButton = mounted.container.querySelector('[aria-label="Move card to another board"]');
    const removeButton = mounted.container.querySelector('[aria-label="Remove card from board"]');

    expect(manaSymbols).not.toBeNull();
    expect(countControls).toBeNull();
    expect(moveButton).toBeNull();
    expect(removeButton).toBeNull();

    mounted.unmount();
  });
});
