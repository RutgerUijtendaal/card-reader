import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test } from 'vitest';
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

const mountCardGalleryItem = async (card: GalleryDisplayItem) => {
  const container = document.createElement('div');
  document.body.appendChild(container);

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
  });
  app.use(router);
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

describe('CardGalleryItem', () => {
  afterEach(() => {
    document.body.innerHTML = '';
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

  test('renders the card skeleton behind the no-image fallback for real cards', async () => {
    const mounted = await mountCardGalleryItem(buildCard());

    expect(mounted.container.textContent).toContain('No image');
    expect(mounted.container.querySelector('.theme-card-loading-shim')).not.toBeNull();
    expect(mounted.container.querySelector('a,button')).not.toBeNull();

    mounted.unmount();
  });
});
