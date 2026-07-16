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
    { id: 'attachment', key: 'attachment', label: 'Attachment' },
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
    useManaTypeGroups().saveGroups([
      {
        id: 'spells',
        name: 'Spells',
        typeKeys: ['spell', 'attachment'],
        excludedTypeKeys: ['follower'],
        isVisible: true,
      },
      {
        id: 'hidden-followers',
        name: 'Hidden followers',
        typeKeys: ['follower', 'attachment'],
        excludedTypeKeys: [],
        isVisible: false,
      },
    ]);
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('renders base-type and saved custom-group statistics with two-decimal averages', async () => {
    const mounted = await mountDistribution();
    const sections = mounted.container.querySelectorAll('[data-testid="mana-statistics-section"]');
    expect(sections).toHaveLength(4);
    expect(sections[0]?.textContent).toContain('All cards');
    expect(sections[0]?.textContent).toContain('Blue Mana');
    expect(sections[0]?.textContent).toContain('2.00');
    expect(sections[0]?.textContent).toContain('1.33');
    expect(Array.from(sections).map((section) => section.querySelector('h4')?.textContent?.trim())).toEqual([
      'All cards',
      'Follower',
      'Spell',
      'Spells',
    ]);
    expect(sections[3]?.textContent).toContain('2.00');
    expect(mounted.container.textContent).not.toContain('Hidden followers');
    mounted.unmount();
  });

  test('renders base-type statistics without requiring custom groups', async () => {
    useManaTypeGroups().saveGroups([]);
    const mounted = await mountDistribution();
    const sectionTitles = Array.from(
      mounted.container.querySelectorAll('[data-testid="mana-statistics-section"] h4'),
    ).map((heading) => heading.textContent?.trim());

    expect(sectionTitles).toEqual(['All cards', 'Follower', 'Spell']);
    mounted.unmount();
  });

  test('opens the group manager from the statistics panel', async () => {
    const mounted = await mountDistribution();
    const manageButton = Array.from(mounted.container.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Add group',
    );
    if (!(manageButton instanceof HTMLButtonElement)) {
      throw new Error('expected add group button');
    }
    manageButton.click();
    await nextTick();
    expect(mounted.container.querySelector('[role="dialog"]')).toBeNull();
    expect(document.body.querySelector('[role="dialog"]')).not.toBeNull();
    mounted.unmount();
  });
});
