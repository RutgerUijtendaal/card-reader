import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardDecklist from '@/domain/cards/components/CardDecklist.vue';
import type { CardListItem } from '@/domain/cards/types';

vi.mock('@/shared/api/client', () => ({
  toAbsoluteApiUrl: (url: string) => url,
}));

const card = (id: string, overrides: Partial<CardListItem> = {}): CardListItem =>
  ({
    id,
    name: `Card ${id}`,
    result_type: 'card',
    card_pool: 'evil',
    card_roles: [],
    card_factions: [],
    card_mana_families: [],
    mana_cost: '2',
    mana_symbols: [],
    mana_value: 2,
    symbols: [],
    types: [],
    image_url: null,
    lifecycle_status: 'active',
    ...overrides,
  }) as unknown as CardListItem;

const cleanups: Array<() => void> = [];

const mountDecklist = async (props: Record<string, unknown>) => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }],
  });
  const target = document.createElement('div');
  document.body.appendChild(target);
  const app = createApp(CardDecklist, { hoverMode: 'none', ...props }).use(router);
  app.mount(target);
  await router.isReady();
  await nextTick();
  cleanups.push(() => {
    app.unmount();
    target.remove();
  });
  return target;
};

const rowTexts = (target: HTMLElement): string[] =>
  Array.from(target.querySelectorAll('[data-testid="card-decklist-row"]')).map((row) =>
    Array.from(row.children, (part) => part.textContent?.trim()).join(' '),
  );

describe('CardDecklist', () => {
  afterEach(() => {
    cleanups.splice(0).forEach((cleanup) => cleanup());
  });

  test('lists each group with its card total and one row per card', async () => {
    const spell = { card: card('a'), quantity: 2 };
    const creature = { card: card('b'), quantity: 3 };
    const target = await mountDecklist({
      entries: [spell, creature],
      groups: [
        { key: 'spell', label: 'Spell', entries: [spell] },
        { key: 'creature', label: 'Creature', entries: [creature] },
      ],
      groupByType: true,
    });

    const titles = Array.from(target.querySelectorAll('h3')).map((title) =>
      Array.from(title.children, (part) => part.textContent).join(' '),
    );
    expect(titles).toEqual(['Spell 2', 'Creature 3']);
    expect(rowTexts(target)).toEqual(['2 Card a 2', '3 Card b 2']);
  });

  test('shows one untitled list when grouping is off', async () => {
    const target = await mountDecklist({
      entries: [{ card: card('a'), quantity: 1 }],
      groups: [],
      groupByType: false,
    });

    expect(target.querySelectorAll('[data-testid="card-decklist-group"]')).toHaveLength(1);
    expect(target.querySelector('h3')).toBeNull();
  });

  test('leaves the cost empty for costless cards and links rows to the card', async () => {
    const target = await mountDecklist({
      entries: [
        { card: card('free', { mana_cost: '-', mana_value: 0 }), quantity: 1 },
        { card: card('zero', { mana_cost: '0', mana_value: 0 }), quantity: 1 },
      ],
      groups: [],
      groupByType: false,
      navigationTarget: (id: string) => `/cards/${id}`,
    });

    expect(target.querySelectorAll('[data-testid="card-decklist-mana"]')).toHaveLength(0);
    expect(target.querySelector('a[href="/cards/free"]')).not.toBeNull();
  });
});
