/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick, reactive, ref, type Component } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import DeckDetailsForm from '@/modules/decks/components/DeckDetailsForm.vue';
import DeckDetailsHeroPanel from '@/modules/decks/components/DeckDetailsHeroPanel.vue';
import DeckHeroSelectionPanel from '@/modules/decks/components/DeckHeroSelectionPanel.vue';

vi.mock('@/api/client', () => ({
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('@/components/decks/DeckTagPicker.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('div', { 'data-testid': 'tag-picker' }, 'Tags');
    },
  }),
}));

const buildController = () => {
  const form = reactive({
    name: 'Aurora Tempo',
    description: 'A compact summary',
    long_description: 'Opening plan\n\nMatchup notes',
    visibility: 'private' as const,
    hero_card_id: 'hero-1',
    tag_ids: [],
    suggested_type_labels: [],
  });
  return {
    isChangingHero: ref(false),
    canApplyHeroChange: ref(false),
    completeInitialHeroSelection: vi.fn(),
    openCards: vi.fn(),
    beginHeroChange: vi.fn(),
    applyHeroChange: vi.fn(),
    cancelHeroChange: vi.fn(),
    deckTagCatalog: ref({ roles: [], types: [] }),
    deck: {
      form,
      selectedHero: ref({
        id: 'hero-1',
        name: 'Aurora Hero',
        image_url: '/hero.png',
      }),
      setupMessages: ref<string[]>([]),
      blockingMessages: ref<string[]>([]),
      setDeckName: vi.fn((value: string) => {
        form.name = value;
      }),
      setDeckDescription: vi.fn((value: string) => {
        form.description = value;
      }),
      setDeckLongDescription: vi.fn((value: string) => {
        form.long_description = value;
      }),
      setDeckVisibility: vi.fn(),
      setDeckTagIds: vi.fn(),
      setSuggestedTypeLabels: vi.fn(),
    },
  };
};

const mountComponent = async (
  component: Component,
  controller = buildController(),
) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp(component, { controller });
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

describe('deck editor mode panels', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  test('keeps initial hero setup focused on hero and required deck name', async () => {
    const mounted = await mountComponent(DeckHeroSelectionPanel);
    const text = mounted.container.textContent ?? '';

    expect(text).toContain('Selected Hero');
    expect(text).toContain('Name *');
    expect(text).toContain('Continue');
    expect(text).not.toContain('Summary');
    expect(text).not.toContain('Long description');
    expect(text).not.toContain('Visibility');
    expect(mounted.container.querySelector('input[required]')).not.toBeNull();

    mounted.unmount();
  });

  test('shows explicit Apply and Cancel controls when replacing a hero', async () => {
    const controller = buildController();
    controller.isChangingHero.value = true;
    controller.canApplyHeroChange.value = false;
    const mounted = await mountComponent(DeckHeroSelectionPanel, controller);
    const buttons = Array.from(mounted.container.querySelectorAll<HTMLButtonElement>('button'));

    expect(mounted.container.querySelector('input[placeholder="Deck name"]')).toBeNull();
    expect(buttons.find((button) => button.textContent?.trim() === 'Apply')?.disabled).toBe(true);
    buttons.find((button) => button.textContent?.trim() === 'Cancel')?.click();
    expect(controller.cancelHeroChange).toHaveBeenCalledTimes(1);

    mounted.unmount();
  });

  test('renders all metadata fields in the wide Details form', async () => {
    const mounted = await mountComponent(DeckDetailsForm);
    const summary = mounted.container.querySelector<HTMLTextAreaElement>('#deck-summary-field');
    const longDescription = mounted.container.querySelector<HTMLTextAreaElement>('#deck-long-description-field');

    expect(mounted.container.querySelector<HTMLInputElement>('#deck-name-field')?.value).toBe('Aurora Tempo');
    expect(summary?.value).toBe('A compact summary');
    expect(summary?.classList.contains('min-h-20')).toBe(true);
    expect(longDescription?.value).toBe('Opening plan\n\nMatchup notes');
    expect(longDescription?.classList.contains('min-h-64')).toBe(true);
    expect(mounted.container.querySelector('[data-testid="tag-picker"]')).not.toBeNull();
    expect(mounted.container.textContent).toContain('Visibility');

    mounted.unmount();
  });

  test('continues from Details to Cards using the form navigation action', async () => {
    const mounted = await mountComponent(DeckDetailsForm);
    const button = Array.from(mounted.container.querySelectorAll<HTMLButtonElement>('button')).find(
      (candidate) => candidate.textContent?.trim() === 'Continue to Cards',
    );

    button?.click();

    expect(button).toBeDefined();
    expect(button?.parentElement?.classList.contains('border-t')).toBe(true);
    expect(button?.parentElement?.classList.contains('theme-divider')).toBe(true);
    expect(mounted.controller.openCards).toHaveBeenCalledTimes(1);

    mounted.unmount();
  });

  test('uses a compact hero sidebar with an explicit Change hero action', async () => {
    const mounted = await mountComponent(DeckDetailsHeroPanel);
    const button = Array.from(mounted.container.querySelectorAll<HTMLButtonElement>('button')).find(
      (candidate) => candidate.textContent?.trim() === 'Change hero',
    );

    expect(mounted.container.textContent).toContain('Aurora Hero');
    expect(mounted.container.querySelector('img')?.parentElement?.className).toContain('max-w-48');
    button?.click();
    expect(mounted.controller.beginHeroChange).toHaveBeenCalledTimes(1);

    mounted.unmount();
  });
});
