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

const mountMarkup = async (hoverMode: 'enlarged' | 'details' | 'enlarged-details') => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp(CardMarkupText, {
    markup: 'See [[card:card-1|Card 1]].',
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
});
