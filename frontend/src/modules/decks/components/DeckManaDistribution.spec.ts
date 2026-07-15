import { createApp, nextTick } from 'vue';
import { afterEach, beforeEach, describe, expect, test } from 'vitest';
import DeckManaDistribution from '@/modules/decks/components/DeckManaDistribution.vue';
import { useManaTypeGroups } from '@/composables/decks/useManaTypeGroups';

const props = {
  entries: [
    {
      quantity: 4,
      card: { mana_symbols: ['blue-mana', 'blue-mana', 'white-mana'], types: [{ key: 'spell' }] },
    },
    {
      quantity: 2,
      card: { mana_symbols: ['white-mana', 'white-mana'], types: [{ key: 'follower' }] },
    },
  ],
  symbols: [
    { key: 'blue-mana', label: 'Blue Mana', symbol_type: 'mana', text_token: '{B}', asset_url: null },
    { key: 'white-mana', label: 'White Mana', symbol_type: 'mana', text_token: '{W}', asset_url: null },
  ],
  types: [
    { id: 'spell', key: 'spell', label: 'Spell' },
    { id: 'follower', key: 'follower', label: 'Follower' },
  ],
};

const mountDistribution = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp(DeckManaDistribution, props);
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

describe('DeckManaDistribution', () => {
  beforeEach(() => {
    localStorage.clear();
    useManaTypeGroups().saveGroups([{ id: 'spells', name: 'Spells', typeKeys: ['spell'] }]);
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('renders overall and saved-group statistics with two-decimal averages', async () => {
    const mounted = await mountDistribution();
    const sections = mounted.container.querySelectorAll('[data-testid="mana-statistics-section"]');
    expect(sections).toHaveLength(2);
    expect(sections[0]?.textContent).toContain('All cards');
    expect(sections[0]?.textContent).toContain('Blue Mana');
    expect(sections[0]?.textContent).toContain('2.00');
    expect(sections[0]?.textContent).toContain('1.33');
    expect(sections[1]?.textContent).toContain('Spells');
    expect(sections[1]?.textContent).toContain('2.00');
    mounted.unmount();
  });

  test('opens the group manager from the statistics panel', async () => {
    const mounted = await mountDistribution();
    const manageButton = Array.from(mounted.container.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Manage groups',
    );
    if (!(manageButton instanceof HTMLButtonElement)) {
      throw new Error('expected manage groups button');
    }
    manageButton.click();
    await nextTick();
    expect(mounted.container.querySelector('[role="dialog"]')).not.toBeNull();
    mounted.unmount();
  });
});
