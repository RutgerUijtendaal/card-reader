/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick, ref } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import type { GalleryDisplayItem } from '@/components/cards/galleryDisplayItems';
import DeckBuilderGallery from '@/modules/decks/components/DeckBuilderGallery.vue';
import type { CardListItem } from '@/modules/card-detail/types';

vi.mock('@/components/cards/CardGalleryItem.vue', () => ({
  default: defineComponent({
    props: {
      card: { type: Object, required: true },
    },
    emits: ['activate'],
    setup(props, { emit, slots, attrs }) {
      return () =>
        h(
          'div',
          {
            ...attrs,
            'data-testid': `gallery-card-${(props.card as { id: string }).id}`,
          },
          [
            h(
              'button',
              {
                type: 'button',
                'data-testid': `activate-${(props.card as { id: string }).id}`,
                onClick: () => emit('activate', props.card),
              },
              'activate',
            ),
            slots.overlay?.(),
          ],
        );
    },
  }),
}));

vi.mock('@/modules/decks/components/DeckCardCountBadge.vue', () => ({
  default: defineComponent({
    props: {
      quantity: { type: Number, required: true },
    },
    setup(props) {
      return () => h('span', { 'data-testid': 'count-badge' }, String(props.quantity));
    },
  }),
}));

const buildCard = (): CardListItem => ({
  id: 'card-1',
  key: 'card-1',
  result_type: 'card',
  image_url: null,
  label: 'Card 1',
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
  symbols: [],
  updated_at: '2025-01-01T00:00:00Z',
  keywords: [],
  tags: [],
  types: [],
});

const buildController = (items: GalleryDisplayItem[]) => {
  const handleGalleryAction = vi.fn();
  const handleGalleryRemoveAction = vi.fn();
  const galleryRemoveActionDisabled = vi.fn((cardId: string) => cardId !== 'card-1');
  const galleryActionDisabled = vi.fn(() => false);
  const getEntryQuantity = vi.fn((cardId: string) => (cardId === 'card-1' ? 2 : 0));

  return {
    gallery: {
      galleryGridStyle: ref({}),
      galleryTileWidthRem: ref(12),
      cardHeightRem: ref(18),
      hasLoadedOnce: ref(true),
      isRefreshing: ref(false),
      loadingShimCount: ref(2),
      galleryCards: ref(items),
      isLoadingPage: ref(false),
      nextPage: ref(null),
      isLoadingInitial: ref(false),
      setLoadMoreSentinel: vi.fn(),
    },
    filters: {
      hoverMode: ref('details'),
    },
    deck: {
      isSetupStep: ref(false),
      galleryActionDisabled,
      galleryRemoveActionDisabled,
      getEntryQuantity,
      handleGalleryAction,
      handleGalleryRemoveAction,
    },
  };
};

const mountGallery = async (controller: ReturnType<typeof buildController>) => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const app = createApp(DeckBuilderGallery, {
    controller,
  });
  app.mount(container);
  await nextTick();

  return {
    container,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('DeckBuilderGallery', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  test('right-click removes eligible cards and prevents the browser context menu', async () => {
    const controller = buildController([buildCard()]);
    const mounted = await mountGallery(controller);
    const card = mounted.container.querySelector('[data-testid="gallery-card-card-1"]');
    if (!(card instanceof HTMLElement)) {
      throw new Error('expected mounted gallery card');
    }

    const event = new MouseEvent('contextmenu', { bubbles: true, cancelable: true });
    card.dispatchEvent(event);
    await nextTick();

    expect(event.defaultPrevented).toBe(true);
    expect(controller.deck.handleGalleryRemoveAction).toHaveBeenCalledWith('card-1');

    mounted.unmount();
  });

  test('right-click still suppresses the browser context menu when removal is unavailable', async () => {
    const controller = buildController([buildCard()]);
    controller.deck.galleryRemoveActionDisabled.mockReturnValue(true);
    const mounted = await mountGallery(controller);
    const card = mounted.container.querySelector('[data-testid="gallery-card-card-1"]');
    if (!(card instanceof HTMLElement)) {
      throw new Error('expected mounted gallery card');
    }

    const event = new MouseEvent('contextmenu', { bubbles: true, cancelable: true });
    card.dispatchEvent(event);
    await nextTick();

    expect(event.defaultPrevented).toBe(true);
    expect(controller.deck.handleGalleryRemoveAction).not.toHaveBeenCalled();

    mounted.unmount();
  });

  test('right-click ignores non-card items and leaves the native context menu alone', async () => {
    const controller = buildController([
      {
        id: 'loading-shim-1',
        result_type: 'loading_shim',
      },
    ]);
    const mounted = await mountGallery(controller);
    const card = mounted.container.querySelector('[data-testid="gallery-card-loading-shim-1"]');
    if (!(card instanceof HTMLElement)) {
      throw new Error('expected mounted loading shim');
    }

    const event = new MouseEvent('contextmenu', { bubbles: true, cancelable: true });
    card.dispatchEvent(event);
    await nextTick();

    expect(event.defaultPrevented).toBe(false);
    expect(controller.deck.handleGalleryRemoveAction).not.toHaveBeenCalled();

    mounted.unmount();
  });

  test('primary add and hover minus controls use the shared controller actions', async () => {
    const controller = buildController([buildCard()]);
    const mounted = await mountGallery(controller);

    const activateButton = mounted.container.querySelector('[data-testid="activate-card-1"]');
    if (!(activateButton instanceof HTMLButtonElement)) {
      throw new Error('expected activate button');
    }

    const buttons = mounted.container.querySelectorAll('button[aria-label]');
    const removeButton = Array.from(buttons).find((button) => button.getAttribute('aria-label') === 'Remove copy from deck');
    if (!(removeButton instanceof HTMLButtonElement)) {
      throw new Error('expected remove button');
    }

    activateButton.click();
    removeButton.click();
    await nextTick();

    expect(controller.deck.handleGalleryAction).toHaveBeenCalledWith(expect.objectContaining({ id: 'card-1' }));
    expect(controller.deck.handleGalleryRemoveAction).toHaveBeenCalledWith('card-1');

    mounted.unmount();
  });
});
