import { createApp, defineComponent, h, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import SmallCardSearchResultRow from '@/domain/cards/components/SmallCardSearchResultRow.vue';
import type { CardListItem } from '@/domain/cards/types';

vi.mock('@/shared/api/client', () => ({
  toAbsoluteApiUrl: (url: string) => url,
}));

const buildCard = (overrides: Partial<CardListItem> = {}): CardListItem => ({
  id: 'card-1',
  key: 'card-1',
  result_type: 'card',
  image_url: '/card.png',
  label: 'Card 1',
  card_pool: 'player' as const, card_roles: [],
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
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
  ...overrides,
});

const mountRow = async ({
  card = buildCard(),
  props = {},
  trailing = false,
}: {
  card?: CardListItem;
  props?: Record<string, unknown>;
  trailing?: boolean;
} = {}) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const activate = vi.fn();
  const app = createApp(
    defineComponent({
      setup() {
        return () =>
          h(
            SmallCardSearchResultRow,
            {
              card,
              onActivate: activate,
              ...props,
            },
            trailing
              ? {
                  trailing: () => h('button', { type: 'button' }, 'Remove'),
                }
              : undefined,
          );
      },
    }),
  );
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

describe('SmallCardSearchResultRow', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('renders card name, rendered player mana symbols, and image when present', async () => {
    const mounted = await mountRow({
      card: buildCard({
        mana_symbols: ['arcane'],
        card_mana_families: ['primal'],
        symbols: [{
          id: 'symbol-1',
          key: 'arcane',
          label: 'Arcane',
          symbol_type: 'mana',
          text_token: '{A}',
          asset_url: '/arcane.svg',
        }],
      }),
    });

    expect(mounted.container.textContent).toContain('Card 1');
    expect(mounted.container.querySelector('[data-testid="row-card-identity"]')?.textContent).toContain('Player');
    expect(mounted.container.querySelector('[data-testid="row-mana-symbols"] img[alt="{A}"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="row-contextual-metadata"]')).toBeNull();
    expect(mounted.container.querySelector('img[alt="Card 1"]')).not.toBeNull();

    mounted.unmount();
  });

  test('uses player mana families when rendered mana symbols are unavailable', async () => {
    const mounted = await mountRow({
      card: buildCard({
        mana_symbols: ['missing-symbol'],
        card_factions: ['order', 'dark'],
        card_mana_families: ['arcane', 'primal'],
      }),
    });

    const identity = mounted.container.querySelector('[data-testid="row-card-identity"]');
    expect(identity?.textContent).toContain('Player');
    expect(identity?.textContent).toContain('Order');
    expect(identity?.textContent).toContain('Dark');
    expect(mounted.container.querySelector('[data-testid="row-mana-symbols"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="row-contextual-metadata"]')?.textContent).toContain('Arcane');
    expect(mounted.container.querySelector('[data-testid="row-contextual-metadata"]')?.textContent).toContain('Primal');

    mounted.unmount();
  });

  test('uses player mana families when a linked symbol has no renderable asset', async () => {
    const mounted = await mountRow({
      card: buildCard({
        mana_symbols: ['arcane'],
        card_mana_families: ['arcane'],
        symbols: [{
          id: 'symbol-1',
          key: 'arcane',
          label: 'Arcane',
          symbol_type: 'mana',
          text_token: '{A}',
          asset_url: null,
        }],
      }),
    });

    expect(mounted.container.querySelector('[data-testid="row-mana-symbols"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="row-contextual-metadata"]')?.textContent).toContain('Arcane');

    mounted.unmount();
  });

  test('uses evil factions as the single metadata row', async () => {
    const mounted = await mountRow({
      card: buildCard({
        card_pool: 'evil',
        card_roles: ['boss'],
        card_factions: ['order', 'dark'],
        card_mana_families: ['occult'],
      }),
    });

    expect(mounted.container.querySelector('[data-testid="row-card-identity"]')?.textContent).toBe('Evil');
    const metadata = mounted.container.querySelector('[data-testid="row-contextual-metadata"]');
    expect(metadata?.textContent).toContain('Order');
    expect(metadata?.textContent).toContain('Dark');
    expect(metadata?.textContent).not.toContain('Boss');
    expect(metadata?.textContent).not.toContain('Occult');

    mounted.unmount();
  });

  test('uses neutral roles as the single metadata row', async () => {
    const mounted = await mountRow({
      card: buildCard({
        card_pool: 'neutral',
        card_roles: ['boon', 'event'],
        card_factions: ['blood'],
        card_mana_families: ['divine'],
      }),
    });

    const identity = mounted.container.querySelector('[data-testid="row-card-identity"]');
    expect(identity?.textContent).toContain('Neutral');
    expect(identity?.textContent).toContain('Blood');
    const metadata = mounted.container.querySelector('[data-testid="row-contextual-metadata"]');
    expect(metadata?.textContent).toContain('Boon');
    expect(metadata?.textContent).toContain('Event');
    expect(metadata?.textContent).not.toContain('Blood');
    expect(metadata?.textContent).not.toContain('Divine');

    mounted.unmount();
  });

  test('does not render synthetic empty metadata labels', async () => {
    const mounted = await mountRow({
      card: buildCard({
        mana_cost: '',
        mana_symbols: [],
        mana_value: null,
        card_roles: [],
        card_factions: [],
        card_mana_families: [],
      }),
    });

    expect(mounted.container.querySelector('[data-testid="row-mana-symbols"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="row-contextual-metadata"]')).toBeNull();
    expect(mounted.container.textContent).not.toContain('Colorless');
    expect(mounted.container.textContent).not.toContain('No faction');
    expect(mounted.container.textContent).not.toContain('Normal');

    mounted.unmount();
  });

  test('renders deprecated status next to the name', async () => {
    const mounted = await mountRow({
      card: buildCard({ lifecycle_status: 'deprecated' }),
    });
    const name = mounted.container.querySelector('[data-testid="row-card-name"]');
    const nameLine = name?.parentElement;

    expect(name?.textContent).toContain('Card 1');
    expect(nameLine?.textContent).toContain('Deprecated');

    mounted.unmount();
  });

  test('emits activate only when interactive and enabled', async () => {
    const mounted = await mountRow();
    const button = mounted.container.querySelector('button');
    if (!(button instanceof HTMLButtonElement)) {
      throw new Error('expected row button');
    }

    button.click();
    await nextTick();

    expect(mounted.activate).toHaveBeenCalledWith(expect.objectContaining({ id: 'card-1' }));

    mounted.unmount();
  });

  test('renders disabled status text without emitting select', async () => {
    const mounted = await mountRow({
      props: {
        disabled: true,
        actionLabel: 'Added',
      },
    });
    const button = mounted.container.querySelector('button');
    if (!(button instanceof HTMLButtonElement)) {
      throw new Error('expected row button');
    }

    button.click();
    await nextTick();

    expect(mounted.container.textContent).toContain('Added');
    expect(mounted.activate).not.toHaveBeenCalled();

    mounted.unmount();
  });

  test('supports locked-in display with trailing content', async () => {
    const mounted = await mountRow({
      props: {
        interactive: false,
        selected: true,
      },
      trailing: true,
    });
    const root = mounted.container.firstElementChild;
    if (!(root instanceof HTMLElement)) {
      throw new Error('expected row root');
    }

    root.click();
    await nextTick();

    expect(root.tagName).toBe('DIV');
    expect(root.getAttribute('aria-selected')).toBe('true');
    expect(mounted.container.textContent).toContain('Remove');
    expect(mounted.activate).not.toHaveBeenCalled();

    mounted.unmount();
  });
});
