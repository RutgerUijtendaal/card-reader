/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick, reactive, ref, type Component } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import DeckDetailsForm from '@/features/decks/components/DeckDetailsForm.vue';
import DeckDetailsHeroPanel from '@/features/decks/components/DeckDetailsHeroPanel.vue';
import DeckHeroSelectionPanel from '@/features/decks/components/DeckHeroSelectionPanel.vue';

vi.mock('@/shared/api/client', () => ({
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('@/domain/decks/components/DeckTagPicker.vue', () => ({
  default: defineComponent({
    props: {
      description: {
        type: String,
        default: undefined,
      },
      sectioned: {
        type: Boolean,
        default: false,
      },
    },
    setup(props) {
      return () => props.sectioned
        ? h('fieldset', { 'data-testid': 'tag-picker', class: 'theme-divider border-t pt-3' }, [
          h('legend', { class: 'pr-2' }, 'Tags'),
          props.description ? h('p', { class: 'mt-1' }, props.description) : null,
        ])
        : h('div', { 'data-testid': 'tag-picker' }, [
          h('p', 'Tags'),
          props.description ? h('p', props.description) : null,
        ]);
    },
  }),
}));

const buildController = () => {
  const form = reactive({
    name: 'Aurora Tempo',
    description: 'A compact summary',
    long_description: 'Opening plan\n\nMatchup notes',
    difficulty: null as 'easy' | 'medium' | 'hard' | null,
    visibility: 'private' as const,
    hero_card_id: 'hero-1',
    tag_ids: [],
    suggested_type_labels: [],
  });
  return {
    isChangingHero: ref(false),
    canApplyHeroChange: ref(false),
    focusDeckNameRequest: ref(0),
    openHero: vi.fn(),
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
      setDeckDifficulty: vi.fn((value: 'easy' | 'medium' | 'hard' | null) => {
        form.difficulty = value;
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
    expect(text).not.toContain('Continue');
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
    const organizationHeading = Array.from(mounted.container.querySelectorAll('h2')).find(
      (heading) => heading.textContent?.trim() === 'Organization',
    );
    const organizationSection = organizationHeading?.closest('section');
    expect(organizationSection?.textContent).toContain('Difficulty');
    expect(organizationSection?.textContent).toContain('Give players a broad sense');
    expect(organizationSection?.textContent).toContain('Tags');
    expect(organizationSection?.textContent).toContain('Make this deck easier to find');
    expect(organizationSection?.textContent).toContain('Visibility');
    expect(organizationSection?.textContent).toContain('Only you can view this deck.');
    const organizationFieldsets = Array.from(
      organizationSection?.querySelectorAll('fieldset') ?? [],
    );
    expect(organizationFieldsets).toHaveLength(3);
    expect(
      organizationFieldsets.map((fieldset) => fieldset.querySelector('legend')?.textContent?.trim()),
    ).toEqual(['Tags', 'Difficulty', 'Visibility']);
    expect(
      organizationFieldsets.every((fieldset) =>
        fieldset.classList.contains('theme-divider')
        && fieldset.classList.contains('border-t'),
      ),
    ).toBe(true);
    const organizationLabels = Array.from(organizationSection?.querySelectorAll('p, legend') ?? [])
      .map((element) => element.textContent?.trim())
      .filter((label) => ['Tags', 'Difficulty', 'Visibility'].includes(label ?? ''));
    expect(organizationLabels).toEqual(['Tags', 'Difficulty', 'Visibility']);
    expect(Array.from(mounted.container.querySelectorAll('h2')).map((heading) => heading.textContent?.trim()))
      .toEqual(['Deck details', 'Organization']);
    const hardButton = Array.from(mounted.container.querySelectorAll<HTMLButtonElement>('button')).find(
      (button) => button.textContent?.trim() === 'Hard',
    );
    hardButton?.click();
    await nextTick();
    expect(hardButton?.getAttribute('aria-pressed')).toBe('true');
    const clearButton = Array.from(mounted.container.querySelectorAll<HTMLButtonElement>('button')).find(
      (button) => button.textContent?.trim() === 'Clear',
    );
    clearButton?.click();
    expect(mounted.controller.deck.setDeckDifficulty).toHaveBeenNthCalledWith(1, 'hard');
    expect(mounted.controller.deck.setDeckDifficulty).toHaveBeenNthCalledWith(2, null);
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
    expect(mounted.controller.openHero).toHaveBeenCalledTimes(1);

    mounted.unmount();
  });
});
