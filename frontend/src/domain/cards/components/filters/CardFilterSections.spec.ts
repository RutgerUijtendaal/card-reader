import { createApp, defineComponent, h, nextTick } from 'vue';
import { afterEach, describe, expect, test } from 'vitest';
import CardFilterSections from '@/domain/cards/components/filters/CardFilterSections.vue';
import { useCardFilterController } from '@/domain/cards/composables/filters/useCardFilterController';
import {
  GALLERY_VISIBLE_FILTER_SECTIONS,
} from '@/domain/cards/utils/filters/cardGalleryFacetPolicy';
import type { CardFilterSectionKey } from '@/domain/cards/utils/filters/cardFilterSectionsState';

const mountSections = async (visibleSections?: readonly CardFilterSectionKey[]) => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const Harness = defineComponent({
    setup() {
      const controller = useCardFilterController();
      return () => h(CardFilterSections, {
        state: controller.filterSectionsState.value,
        showCardPool: false,
        visibleSections,
      });
    },
  });

  const app = createApp(Harness);
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
});
