import { createApp, h, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import PlaytestStack from '@/modules/playtester/components/PlaytestStack.vue';
import type { DeckCardSummary } from '@/modules/decks/types';
import type { PlaytestCardInstance, PlaytestZoneId } from '@/modules/playtester/types';

vi.mock('@/api/client', () => ({
  toAbsoluteApiUrl: (url: string) => url,
}));

const baseCard = {
  id: 'card-1',
  key: 'card-1',
  label: 'Card 1',
  result_type: 'card',
  image_url: null,
  is_hero: false,
  lifecycle_status: 'active',
  template_id: '',
  version_id: 'card-1-version',
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  name: 'Card 1',
  type_line: '',
  mana_cost: '',
  mana_symbols: [],
  mana_value: 1,
  attack: null,
  health: null,
  rules_text: '',
  confidence: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
} satisfies DeckCardSummary;

const createInstance = (
  zoneId: PlaytestZoneId,
  instanceId: string,
  card: DeckCardSummary,
  order: number,
): PlaytestCardInstance => ({
  instanceId,
  cardId: card.id,
  card,
  zoneId,
  order,
  tapped: false,
  face: 'front',
  setupOrigin: false,
  boardX: null,
  boardY: null,
  pileGroupId: null,
  pileOrder: null,
});

const mountStack = (props: Partial<InstanceType<typeof PlaytestStack>['$props']> = {}) => {
  const container = document.createElement('div');
  document.body.append(container);
  const app = createApp({
    render: () => h(PlaytestStack, {
      zoneId: 'discard',
      label: 'Discard',
      instances: [],
      face: 'front',
      cardBackUrl: null,
      collapsed: false,
      defaultAction: 'open',
      draggingTop: false,
      ...props,
    }),
  });
  app.mount(container);

  return {
    container,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

const middleClick = (element: Element): void => {
  element.dispatchEvent(new MouseEvent('pointerdown', {
    bubbles: true,
    button: 1,
  }));
};

describe('PlaytestStack', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('middle click zooms only the visible top card', async () => {
    const firstCard = { ...baseCard, id: 'card-1', key: 'card-1', label: 'Bottom Card', name: 'Bottom Card' };
    const topCard = { ...baseCard, id: 'card-2', key: 'card-2', label: 'Top Card', name: 'Top Card' };
    const mounted = mountStack({
      instances: [
        createInstance('discard', 'bottom-instance', firstCard, 0),
        createInstance('discard', 'top-instance', topCard, 1),
      ],
    });

    middleClick(mounted.container.querySelector('[data-testid="playtest-discard-zone"]') as Element);
    await nextTick();

    const overlay = document.body.querySelector('[data-testid="playtest-stack-zoom-overlay"]');
    expect(overlay).not.toBeNull();
    expect(overlay?.textContent).toContain('Top Card');
    expect(overlay?.textContent).not.toContain('Bottom Card');

    mounted.unmount();
  });

  test('middle click zooms the face-down library top as the card back', async () => {
    const firstCard = { ...baseCard, id: 'card-1', key: 'card-1', label: 'Library Top', name: 'Library Top' };
    const secondCard = { ...baseCard, id: 'card-2', key: 'card-2', label: 'Library Bottom', name: 'Library Bottom' };
    const mounted = mountStack({
      zoneId: 'library',
      label: 'Library',
      face: 'back',
      cardBackUrl: '/card-back.png',
      instances: [
        createInstance('library', 'top-instance', firstCard, 0),
        createInstance('library', 'bottom-instance', secondCard, 1),
      ],
    });

    middleClick(mounted.container.querySelector('[data-testid="playtest-library-zone"]') as Element);
    await nextTick();

    const overlay = document.body.querySelector('[data-testid="playtest-stack-zoom-overlay"]');
    const image = overlay?.querySelector('img');
    expect(image?.getAttribute('src')).toBe('/card-back.png');
    expect(image?.getAttribute('alt')).toBe('Library top card');
    expect(overlay?.textContent).not.toContain('Library Top');

    mounted.unmount();
  });

  test('pointer release closes the stack zoom overlay', async () => {
    const mounted = mountStack({
      instances: [
        createInstance('discard', 'top-instance', { ...baseCard, name: 'Top Card' }, 0),
      ],
    });
    const stack = mounted.container.querySelector('[data-testid="playtest-discard-zone"]') as Element;

    middleClick(stack);
    await nextTick();
    expect(document.body.querySelector('[data-testid="playtest-stack-zoom-overlay"]')).not.toBeNull();

    stack.dispatchEvent(new MouseEvent('pointerup', { bubbles: true }));
    await nextTick();
    expect(document.body.querySelector('[data-testid="playtest-stack-zoom-overlay"]')).toBeNull();

    mounted.unmount();
  });
});
