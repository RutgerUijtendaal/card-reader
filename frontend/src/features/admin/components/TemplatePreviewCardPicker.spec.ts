import { createApp, nextTick } from 'vue';
import { afterEach, describe, expect, test } from 'vitest';
import TemplatePreviewCardPicker from '@/features/admin/components/TemplatePreviewCardPicker.vue';

afterEach(() => {
  document.body.innerHTML = '';
});

describe('TemplatePreviewCardPicker', () => {
  test('labels same-named preview cards by pool', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const app = createApp(TemplatePreviewCardPicker, {
      cards: [
        {
          id: 'player-card',
          label: 'Shared Card',
          name: 'Shared Card',
          card_pool: 'player',
          template_id: 'mtg-like-v1',
          image_url: null,
        },
        {
          id: 'evil-card',
          label: 'Shared Card',
          name: 'Shared Card',
          card_pool: 'evil',
          template_id: 'mtg-like-v1',
          image_url: null,
        },
      ],
      loading: false,
      scope: 'current-template',
      searchQuery: '',
      selectedCard: null,
      templateScopeAvailable: true,
    });
    app.mount(container);
    await nextTick();

    const input = container.querySelector('input');
    input?.dispatchEvent(new FocusEvent('focus'));
    await nextTick();

    expect(container.textContent).toContain('Player · Shared Card · mtg-like-v1');
    expect(container.textContent).toContain('Evil · Shared Card · mtg-like-v1');

    app.unmount();
  });
});
