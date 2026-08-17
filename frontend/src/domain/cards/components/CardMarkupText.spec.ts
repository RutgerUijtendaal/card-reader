import { createApp, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardMarkupText from '@/domain/cards/components/CardMarkupText.vue';
import type { CardListItem } from '@/domain/cards/types';
import { fetchHoverPreviewCard } from '@/domain/cards/utils/cardHoverPreview';

vi.mock('@/domain/cards/utils/cardHoverPreview', () => ({
  fetchHoverPreviewCard: vi.fn(),
}));

const fetchHoverPreviewCardMock = vi.mocked(fetchHoverPreviewCard);

const card: CardListItem = {
  id: 'card-1',
  key: 'card-1',
  result_type: 'card',
  image_url: '/cards/card-1/image',
  label: 'Card 1',
  card_pool: 'player',
  card_roles: [],
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
  type_line: 'Spell',
  rules_text: 'Deal damage.',
  confidence: 1,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
};

const mountMarkup = async (
  hoverMode: 'enlarged' | 'details' | 'enlarged-details',
  markup = 'See [[card:card-1|Card 1]].',
) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp(CardMarkupText, {
    markup,
    hoverMode,
  });
  app.mount(container);
  await nextTick();
  const link = container.querySelector('a');
  if (!(link instanceof HTMLAnchorElement)) throw new Error('Expected card link.');
  link.dispatchEvent(new MouseEvent('pointerover', { bubbles: true }));
  await Promise.resolve();
  await nextTick();
  return { app, container };
};

describe('CardMarkupText', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  test('renders card-only hover mode without the details tooltip shell', async () => {
    fetchHoverPreviewCardMock.mockResolvedValue(card);
    const mounted = await mountMarkup('enlarged');

    expect(document.body.querySelector('.card-hover-tooltip')).toBeNull();
    expect(document.body.querySelector('img[alt="Card 1"]')).not.toBeNull();
    expect(document.body.textContent).not.toContain('Type Line');

    mounted.app.unmount();
    mounted.container.remove();
  });

  test('keeps the details tooltip shell for combined hover mode', async () => {
    fetchHoverPreviewCardMock.mockResolvedValue(card);
    const mounted = await mountMarkup('enlarged-details');

    expect(document.body.querySelector('.card-hover-tooltip')).not.toBeNull();
    expect(document.body.textContent).toContain('Type Line');

    mounted.app.unmount();
    mounted.container.remove();
  });

  test('closes the preview after the pointer leaves its teleported panel', async () => {
    fetchHoverPreviewCardMock.mockResolvedValue(card);
    const mounted = await mountMarkup('enlarged');
    const link = mounted.container.querySelector('a');
    const panel = document.body.querySelector('.z-50');
    if (!(link instanceof HTMLAnchorElement) || !(panel instanceof HTMLElement)) {
      throw new Error('Expected a linked-text preview.');
    }

    link.dispatchEvent(new MouseEvent('pointerout', { bubbles: true, relatedTarget: panel }));
    await nextTick();
    expect(document.body.querySelector('.z-50')).not.toBeNull();

    panel.dispatchEvent(new MouseEvent('pointerleave', { bubbles: true }));
    await nextTick();
    expect(document.body.querySelector('.z-50')).toBeNull();

    mounted.app.unmount();
    mounted.container.remove();
  });

  test('keeps link activation from toggling a surrounding interactive panel', async () => {
    const mounted = await mountMarkup(
      'enlarged',
      '[External](https://example.com) and [[card:card-1|Card 1]]',
    );
    let parentActivations = 0;
    mounted.container.addEventListener('click', () => { parentActivations += 1; });
    mounted.container.addEventListener('keydown', () => { parentActivations += 1; });

    for (const link of mounted.container.querySelectorAll('a')) {
      const click = new MouseEvent('click', { bubbles: true, cancelable: true });
      click.preventDefault();
      link.dispatchEvent(click);
      link.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    }
    expect(parentActivations).toBe(0);

    mounted.app.unmount();
    mounted.container.remove();
  });
});
