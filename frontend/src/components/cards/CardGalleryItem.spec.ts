import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardGalleryItem from '@/components/cards/CardGalleryItem.vue';
import type { GalleryDisplayItem } from '@/components/cards/galleryDisplayItems';
import type { CardListItem } from '@/modules/card-detail/types';

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

const buildCardWithImage = (): CardListItem => ({
  ...buildCard(),
  image_url: '/cards/card-1/image',
});

const mountCardGalleryItem = async (
  card: GalleryDisplayItem,
  props: Record<string, unknown> = {},
) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const activate = vi.fn();

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/cards', component: { template: '<div />' } },
      { path: '/cards/:id', component: { template: '<div />' } },
    ],
  });
  await router.push('/cards');
  await router.isReady();

  const app = createApp(CardGalleryItem, {
    card,
    onActivate: activate,
    ...props,
  });
  app.use(router);
  app.mount(container);
  await nextTick();

  return {
    container,
    activate,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('CardGalleryItem', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  test('renders the non-interactive loading shim layout regions', async () => {
    const mounted = await mountCardGalleryItem({
      id: 'loading-shim-1',
      result_type: 'loading_shim',
    });

    expect(mounted.container.querySelector('.theme-card-loading-shim')).not.toBeNull();
    expect(mounted.container.querySelector('.theme-card-loading-shim-header')).not.toBeNull();
    expect(mounted.container.querySelector('.theme-card-loading-shim-art')).not.toBeNull();
    expect(mounted.container.querySelector('.theme-card-loading-shim-middle')).not.toBeNull();
    expect(mounted.container.querySelector('.theme-card-loading-shim-rules')).not.toBeNull();
    expect(mounted.container.querySelector('button')).toBeNull();
    expect(mounted.container.querySelector('a')).toBeNull();

    mounted.unmount();
  });

  test('renders the card skeleton as the no-image fallback for real cards', async () => {
    const mounted = await mountCardGalleryItem(buildCard());

    expect(mounted.container.textContent).not.toContain('No image');
    expect(mounted.container.querySelector('.theme-card-loading-shim')).not.toBeNull();
    expect(mounted.container.querySelector('a,button')).not.toBeNull();

    mounted.unmount();
  });

  test('mouse-activated emitted cards release focus on fine pointer screens', async () => {
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })));
    const mounted = await mountCardGalleryItem(buildCard(), {
      activationMode: 'emit',
      activationLabel: 'Add card to deck',
    });
    const button = mounted.container.querySelector('button');
    if (!(button instanceof HTMLButtonElement)) {
      throw new Error('expected activation button');
    }

    button.focus();
    expect(document.activeElement).toBe(button);

    button.click();
    await nextTick();

    expect(mounted.activate).toHaveBeenCalledWith(expect.objectContaining({ id: 'card-1' }));
    expect(document.activeElement).not.toBe(button);

    mounted.unmount();
  });

  test('mouse leave clears focused descendants on fine pointer screens', async () => {
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })));
    const mounted = await mountCardGalleryItem(buildCard(), {
      activationMode: 'emit',
      activationLabel: 'Add card to deck',
    });
    const button = mounted.container.querySelector('button');
    if (!(button instanceof HTMLButtonElement)) {
      throw new Error('expected activation button');
    }

    button.focus();
    expect(document.activeElement).toBe(button);

    const root = mounted.container.firstElementChild;
    if (!(root instanceof HTMLElement)) {
      throw new Error('expected card root');
    }
    root.dispatchEvent(new MouseEvent('mouseleave', { bubbles: true }));
    await nextTick();

    expect(document.activeElement).not.toBe(button);

    mounted.unmount();
  });

  test('does not render a hover overlay when hover previews are disabled', async () => {
    const mounted = await mountCardGalleryItem(buildCardWithImage(), {
      hoverMode: 'none',
    });
    const root = mounted.container.firstElementChild;
    if (!(root instanceof HTMLElement)) {
      throw new Error('expected card root');
    }

    root.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    await nextTick();

    expect(document.body.querySelector('.shared-element-hover-panel')).toBeNull();

    mounted.unmount();
  });

  test('renders enlarged hovers through the shared-element overlay', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false })));
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      const id = window.setTimeout(() => callback(performance.now()), 16);
      return Number(id);
    });
    vi.stubGlobal('cancelAnimationFrame', (id: number) => {
      clearTimeout(id);
    });
    const mounted = await mountCardGalleryItem(buildCardWithImage(), {
      hoverMode: 'enlarged',
    });
    const root = mounted.container.firstElementChild;
    if (!(root instanceof HTMLElement)) {
      throw new Error('expected card root');
    }

    root.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    await nextTick();

    const panel = document.body.querySelector<HTMLElement>('.shared-element-hover-panel');
    expect(panel).not.toBeNull();
    expect(panel?.style.position).toBe('fixed');
    expect(panel?.style.transformOrigin).toBe('top left');

    await nextTick();
    await vi.runOnlyPendingTimersAsync();
    await nextTick();

    expect(document.body.querySelector('.shared-element-hover-panel-open')).not.toBeNull();

    mounted.unmount();
  });

  test('reduced-motion hover overlays skip transform animation', async () => {
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })));
    const mounted = await mountCardGalleryItem(buildCardWithImage(), {
      hoverMode: 'enlarged',
    });
    const root = mounted.container.firstElementChild;
    if (!(root instanceof HTMLElement)) {
      throw new Error('expected card root');
    }

    root.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    await nextTick();

    expect(document.body.querySelector('.shared-element-hover-panel-reduced-motion')).not.toBeNull();

    mounted.unmount();
  });
});
