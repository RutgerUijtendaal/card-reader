import { createApp, nextTick } from 'vue';
import { afterEach, describe, expect, test } from 'vitest';
import DeckTagPills from '@/components/decks/DeckTagPills.vue';

afterEach(() => {
  document.body.innerHTML = '';
});

const mountPills = async (maxVisible: number) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp(DeckTagPills, {
    tags: [
      { id: 'type-armor', kind: 'type', key: 'armor', label: 'Armor' },
      { id: 'role-control', kind: 'role', key: 'control', label: 'Control' },
      { id: 'type-draw', kind: 'type', key: 'draw', label: 'Card Draw' },
    ],
    pendingSuggestions: [
      {
        id: 'suggestion-tempo',
        kind: 'type',
        label: 'Tempo',
        normalized_value: 'tempo',
        status: 'pending',
      },
      {
        id: 'suggestion-ramp',
        kind: 'type',
        label: 'Ramp',
        normalized_value: 'ramp',
        status: 'pending',
      },
    ],
    maxVisible,
  });
  app.mount(container);
  await nextTick();
  return { app, container };
};

describe('DeckTagPills', () => {
  test('caps assigned and pending pills together with roles first', async () => {
    const { app, container } = await mountPills(4);
    const labels = [...container.querySelectorAll(':scope > div > *')].map((pill) => pill.textContent?.trim());
    const expandButton = container.querySelector<HTMLButtonElement>('button[aria-label="Show all 5 deck tags"]');

    expect(labels).toEqual(['Control', 'Armor', 'Card Draw', 'Tempo · Pending', '+1']);
    expect(container.textContent).not.toContain('Ramp');
    expect(expandButton?.getAttribute('aria-expanded')).toBe('false');

    expandButton?.click();
    await nextTick();

    expect(container.textContent).toContain('Ramp · Pending');
    expect(container.textContent).not.toContain('+1');
    expect(container.querySelector('button[aria-label="Show all 5 deck tags"]')).toBeNull();

    app.unmount();
  });

  test('shows every assigned and pending pill when unlimited', async () => {
    const { app, container } = await mountPills(0);

    expect(container.textContent).toContain('Tempo · Pending');
    expect(container.textContent).toContain('Ramp · Pending');
    expect(container.textContent).not.toContain('+1');

    app.unmount();
  });
});
