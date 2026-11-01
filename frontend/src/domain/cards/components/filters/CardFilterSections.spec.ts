import { createApp, defineComponent, h, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardFilterSections from '@/domain/cards/components/filters/CardFilterSections.vue';
import { useCardFilterController } from '@/domain/cards/composables/filters/useCardFilterController';
import {
  GALLERY_VISIBLE_FILTER_SECTIONS,
} from '@/domain/cards/utils/filters/cardGalleryFacetPolicy';
import type { CardFilterSectionKey } from '@/domain/cards/utils/filters/cardFilterSectionsState';

const mountSections = async (
  visibleSections?: readonly CardFilterSectionKey[],
  barOptions?: { onReset: () => void; hasActiveState?: boolean },
) => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  let controller!: ReturnType<typeof useCardFilterController>;
  const Harness = defineComponent({
    setup() {
      controller = useCardFilterController();
      return () => h(CardFilterSections, {
        state: controller.filterSectionsState.value,
        showCardPool: false,
        visibleSections,
        ...(barOptions ? { layout: 'bar', ...barOptions } : {}),
      });
    },
  });

  const app = createApp(Harness);
  app.mount(container);
  await nextTick();

  return {
    container,
    controller,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('CardFilterSections', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('keeps the complete classification surface for global consumers by default', async () => {
    const mounted = await mountSections();
    const text = mounted.container.textContent ?? '';

    expect(text).toContain('Card roles');
    expect(text).toContain('Factions');
    expect(text).toContain('Mana');
    expect(text).toContain('Affinity');
    expect(text).toContain('Devotion');

    mounted.unmount();
  });

  test.each([
    ['player', ['Mana', 'Types', 'Affinity', 'Devotion', 'Generic', 'Keywords', 'Tags']],
    ['evil', ['Factions', 'Types', 'Generic', 'Keywords', 'Tags']],
    ['neutral', ['Types', 'Generic', 'Keywords', 'Tags']],
  ] as const)('renders only the %s Gallery sections', async (cardPool, expectedLabels) => {
    const mounted = await mountSections(GALLERY_VISIBLE_FILTER_SECTIONS[cardPool]);
    const text = mounted.container.textContent ?? '';

    expectedLabels.forEach((label) => expect(text).toContain(label));
    expect(text).not.toContain('Card roles');
    expect(text.includes('Factions')).toBe(cardPool === 'evil');
    expect(text.includes('Mana')).toBe(cardPool === 'player');
    expect(text.includes('Affinity')).toBe(cardPool === 'player');
    expect(text.includes('Devotion')).toBe(cardPool === 'player');

    mounted.unmount();
  });

  test('bar layout turns each visible section into a chip whose popover holds the same controls', async () => {
    const onReset = vi.fn();
    const mounted = await mountSections(GALLERY_VISIBLE_FILTER_SECTIONS.player, { onReset });
    const chips = Array.from(mounted.container.querySelectorAll<HTMLButtonElement>('button[aria-expanded]'));

    expect(chips.map((chip) => chip.textContent?.trim())).toEqual([
      'Mana',
      'Types',
      'Generic',
      'Keywords',
      'Tags',
      'Affinity',
      'Devotion',
    ]);
    expect(mounted.container.textContent).not.toContain('Clear filters');

    chips[0].click();
    await nextTick();
    const panel = document.body.querySelector('[role="dialog"][aria-label="Mana filter"]');
    expect(panel?.textContent).toContain('Cost');
    expect(panel?.querySelector('[aria-label="Reset group"]')).not.toBeNull();

    const input = panel!.querySelector<HTMLInputElement>('input[type="number"]')!;
    input.value = '2';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await nextTick();
    expect(chips[0].textContent).toContain('1');
    const clear = Array.from(mounted.container.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Clear filters',
    );
    clear?.click();
    expect(onReset).toHaveBeenCalledOnce();

    mounted.unmount();
  });

  test.each([
    ['Mana', 0, 'manaCostMin'],
    ['Mana', 1, 'manaCostMax'],
    ['Generic', 0, 'attackMin'],
    ['Generic', 1, 'attackMax'],
    ['Generic', 2, 'healthMin'],
    ['Generic', 3, 'healthMax'],
  ] as const)('normalizes %s input %s and clears its active range', async (label, index, field) => {
    const mounted = await mountSections(GALLERY_VISIBLE_FILTER_SECTIONS.player, {
      onReset: vi.fn(),
    });
    const chip = Array.from(
      mounted.container.querySelectorAll<HTMLButtonElement>('button[aria-expanded]'),
    ).find((button) => button.textContent?.trim() === label)!;
    chip.click();
    await nextTick();
    const panel = document.body.querySelector(`[role="dialog"][aria-label="${label} filter"]`)!;
    const input = panel.querySelectorAll<HTMLInputElement>('input[type="number"]')[index];

    for (const value of ['0', '2', '']) {
      input.value = value;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      await nextTick();
      expect(mounted.controller.filterSectionsState.value[field]).toBe(value);
      expect(chip.textContent?.trim()).toBe(value ? `${label}1` : label);
      expect(mounted.container.textContent?.includes('Clear filters')).toBe(Boolean(value));
    }

    mounted.unmount();
  });

  test('bar layout offers Clear filters for state the sections cannot count', async () => {
    const mounted = await mountSections(GALLERY_VISIBLE_FILTER_SECTIONS.neutral, {
      onReset: () => undefined,
      hasActiveState: true,
    });

    expect(mounted.container.textContent).toContain('Clear filters');

    mounted.unmount();
  });
});
