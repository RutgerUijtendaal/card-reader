import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test } from 'vitest';
import CatalogLinkedCardsGrid from '@/features/admin/components/CatalogLinkedCardsGrid.vue';

afterEach(() => {
  document.body.innerHTML = '';
});

describe('CatalogLinkedCardsGrid', () => {
  test('shows pool and role badges without requiring hover', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const app = createApp(CatalogLinkedCardsGrid, {
      cards: [
        {
          card_id: 'card-1',
          card_label: 'The Offer',
          card_version_id: 'version-1',
          card_version_name: 'The Offer',
          image_url: null,
          card_pool: 'game_master',
          card_roles: ['boon', 'event'],
        },
      ],
      emptyMessage: 'No cards',
    });
    const routeStub = { render: (): null => null };
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: routeStub },
        { path: '/cards/:cardId/edit', component: routeStub },
      ],
    });
    app.use(router);
    await router.push('/');
    await router.isReady();
    app.mount(container);
    await nextTick();

    expect(container.textContent).toContain('Game Master');
    expect(container.textContent).toContain('Boon');
    expect(container.textContent).toContain('Event');

    app.unmount();
  });
});
