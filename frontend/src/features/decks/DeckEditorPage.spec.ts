/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import DeckEditorPage from '@/features/decks/DeckEditorPage.vue';

const { controller } = vi.hoisted(() => {
  const refValue = <T,>(value: T) => ({ value, __v_isRef: true });

  return {
    controller: {
      deckId: refValue('deck-1'),
      backLink: refValue('/my/decks'),
      backLabel: refValue('Back to My Decks'),
      editorMode: refValue<'hero' | 'details' | 'cards'>('cards'),
      isChangingHero: refValue(false),
      saving: refValue(false),
      manualSaving: refValue(false),
      loading: refValue(false),
      hasUnsavedChanges: refValue(true),
      canAutosync: refValue(true),
      changeStatusLabel: refValue('Unsaved'),
      autosyncEnabled: refValue(false),
      discardChangesModalOpen: refValue(false),
      deckBuildingRules: refValue({
        mainboard_card_count: { min: 40, max: 60 },
        mana_type_count: { min: 10 },
      }),
      saveDeck: vi.fn(),
      openDetails: vi.fn(),
      openCards: vi.fn(),
      confirmDiscardChanges: vi.fn(),
      cancelDiscardChanges: vi.fn(),
      deck: {
        overallTotalCards: refValue(42),
        totalMainboardCards: refValue(40),
        totalMainboardManaTypeCards: refValue(12),
        hasFreeMulliganManaRatio: refValue(true),
        headerDeckTypeCounts: refValue([
          { type: { id: 'type-spell', label: 'Spell' }, count: 18 },
        ]),
        remainingDeckTypeCount: refValue(0),
        validationMessages: refValue<string[]>([]),
        warningMessages: refValue<string[]>([]),
        overallUniqueCards: refValue(28),
        isDeckValid: refValue(true),
        deckStatusLabel: refValue('Ready'),
      },
    },
  };
});

vi.mock('@/features/decks/composables/useDeckEditor', () => ({
  useDeckEditor: () => controller,
}));

vi.mock('@/shared/components/app/AppPageHeader.vue', () => ({
  default: defineComponent({
    props: {
      title: { type: String, required: true },
    },
    setup(props, { slots }) {
      return () =>
        h('header', [
          h('h1', props.title),
          slots.actions?.(),
        ]);
    },
  }),
}));

vi.mock('@/shared/components/app/AppPageLayout.vue', () => ({
  default: defineComponent({
    setup(_, { slots }) {
      return () =>
        h('main', { 'data-testid': 'builder-layout' }, [
          slots.aside?.(),
          slots.default?.(),
          slots.endAside?.(),
        ]);
    },
  }),
}));

vi.mock('@/shared/components/InfoTooltip.vue', () => ({
  default: defineComponent({
    setup(_, { slots }) {
      return () => h('span', slots.default?.({ tooltipId: 'mock-tooltip' }));
    },
  }),
}));

vi.mock('@/shared/components/modals/ConfirmModal.vue', () => ({
  default: defineComponent({
    props: {
      open: { type: Boolean, required: true },
      title: { type: String, required: true },
      message: { type: String, required: true },
      confirmLabel: { type: String, required: true },
      cancelLabel: { type: String, required: true },
    },
    setup(props, { emit }) {
      return () =>
        props.open
          ? h('section', { 'data-testid': 'confirm-modal' }, [
              h('h2', props.title),
              h('p', props.message),
              h('button', { onClick: () => emit('cancel') }, props.cancelLabel),
              h('button', { onClick: () => emit('confirm') }, props.confirmLabel),
            ])
          : null;
    },
  }),
}));

vi.mock('@/features/decks/components/DeckBuilderFiltersPanel.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('aside', 'Filters');
    },
  }),
}));

vi.mock('@/features/decks/components/DeckBuilderGallery.vue', () => ({
  default: defineComponent({
    props: {
      loading: { type: Boolean, default: false },
    },
    setup(props) {
      return () => h('section', {
        'data-testid': 'builder-gallery',
        'data-loading': String(props.loading),
      }, 'Gallery');
    },
  }),
}));

vi.mock('@/features/decks/components/DeckBuilderSummaryPanel.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('aside', 'Summary');
    },
  }),
}));

vi.mock('@/features/decks/components/DeckHeroSelectionPanel.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('aside', { 'data-testid': 'hero-selection-panel' }, 'Hero selection');
    },
  }),
}));

vi.mock('@/features/decks/components/DeckDetailsHeroPanel.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('aside', { 'data-testid': 'details-hero-panel' }, 'Deck hero');
    },
  }),
}));

vi.mock('@/features/decks/components/DeckDetailsForm.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('section', { 'data-testid': 'details-form' }, 'Deck details form');
    },
  }),
}));

const mountPage = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp(DeckEditorPage);
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

describe('DeckEditorPage', () => {
  afterEach(() => {
    controller.deckId.value = 'deck-1';
    controller.editorMode.value = 'cards';
    controller.isChangingHero.value = false;
    controller.loading.value = false;
    controller.saving.value = false;
    controller.manualSaving.value = false;
    controller.changeStatusLabel.value = 'Unsaved';
    controller.hasUnsavedChanges.value = true;
    controller.canAutosync.value = true;
    controller.autosyncEnabled.value = false;
    controller.discardChangesModalOpen.value = false;
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  test('renders deck builder status bar between the asides and above the gallery', async () => {
    const mounted = await mountPage();
    const statusBar = mounted.container.querySelector<HTMLElement>('[aria-label="Deck builder status"]');
    const leftAside = Array.from(mounted.container.querySelectorAll('aside')).find((aside) => aside.textContent === 'Filters');
    const gallery = mounted.container.querySelector<HTMLElement>('[data-testid="builder-gallery"]');
    const rightAside = Array.from(mounted.container.querySelectorAll('aside')).find((aside) => aside.textContent === 'Summary');
    const autosyncCheckbox = statusBar?.querySelector<HTMLInputElement>('input[type="checkbox"]');

    if (!statusBar || !leftAside || !gallery || !rightAside) {
      throw new Error('expected builder layout landmarks');
    }
    expect(leftAside.compareDocumentPosition(statusBar) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(statusBar.compareDocumentPosition(gallery) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(gallery.compareDocumentPosition(rightAside) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(statusBar?.textContent).toContain('Unsaved');
    expect(statusBar?.textContent).toContain('Autosync');
    expect(statusBar?.textContent).toContain('Total');
    expect(statusBar?.textContent).toContain('42');
    expect(statusBar?.textContent).toContain('Ready');
    expect(autosyncCheckbox?.disabled).toBe(false);
    expect(gallery.parentElement?.classList.contains('deck-builder-gallery-scroll')).toBe(true);
    expect(gallery.parentElement?.classList.contains('app-scrollbar')).toBe(true);

    mounted.unmount();
  });

  test('renders hero browsing without the cards status or board sidebar', async () => {
    controller.deckId.value = '';
    controller.editorMode.value = 'hero';

    const mounted = await mountPage();

    expect(mounted.container.querySelector('[aria-label="Deck builder status"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="builder-gallery"]')).not.toBeNull();
    expect(
      mounted.container
        .querySelector('[data-testid="builder-gallery"]')
        ?.parentElement?.classList.contains('deck-builder-gallery-scroll'),
    ).toBe(true);
    expect(mounted.container.querySelector('[data-testid="hero-selection-panel"]')).not.toBeNull();
    expect(mounted.container.textContent).toContain('Filters');
    expect(mounted.container.textContent).not.toContain('Summary');

    mounted.unmount();
    controller.deckId.value = 'deck-1';
  });

  test('renders the wide details layout without a gallery or board sidebar', async () => {
    controller.editorMode.value = 'details';

    const mounted = await mountPage();

    expect(mounted.container.querySelector('[data-testid="details-hero-panel"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="details-form"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="builder-gallery"]')).toBeNull();
    expect(mounted.container.textContent).not.toContain('Filters');
    expect(mounted.container.textContent).not.toContain('Summary');

    mounted.unmount();
  });

  test('renders a details-shaped loading state while the deck loads', async () => {
    controller.editorMode.value = 'details';
    controller.loading.value = true;

    const mounted = await mountPage();

    expect(mounted.container.querySelector('[data-testid="builder-layout"]')).not.toBeNull();
    expect(mounted.container.querySelectorAll('.deck-builder-loading-panel')).toHaveLength(1);
    expect(mounted.container.querySelector('[data-testid="builder-gallery"]')).toBeNull();
    expect(mounted.container.textContent).not.toContain('Loading deck...');
    expect(mounted.container.textContent).not.toContain('Filters');
    expect(mounted.container.textContent).not.toContain('Summary');

    mounted.unmount();
  });

  test('keeps the shared gallery mounted in its loading state while Cards initializes', async () => {
    controller.editorMode.value = 'cards';
    controller.loading.value = true;

    const mounted = await mountPage();
    const gallery = mounted.container.querySelector('[data-testid="builder-gallery"]');

    expect(mounted.container.querySelectorAll('.deck-builder-loading-panel')).toHaveLength(2);
    expect(gallery?.getAttribute('data-loading')).toBe('true');
    expect(mounted.container.querySelector('.deck-builder-gallery-scroll')).not.toBeNull();
    expect(mounted.container.querySelector('[aria-label="Deck builder status"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="details-form"]')).toBeNull();

    mounted.unmount();
  });

  test('switches between Details and Cards from persistent header tabs', async () => {
    controller.editorMode.value = 'details';
    const mounted = await mountPage();
    const detailsTab = mounted.container.querySelector<HTMLButtonElement>('button[aria-label="Open deck details"]');
    const cardsTab = mounted.container.querySelector<HTMLButtonElement>('button[aria-label="Open deck cards"]');

    expect(detailsTab?.getAttribute('aria-pressed')).toBe('true');
    expect(cardsTab?.getAttribute('aria-pressed')).toBe('false');
    cardsTab?.click();
    await nextTick();

    expect(controller.openCards).toHaveBeenCalledTimes(1);
    mounted.unmount();
  });

  test('hides section tabs during explicit hero replacement', async () => {
    controller.editorMode.value = 'hero';
    controller.isChangingHero.value = true;
    const mounted = await mountPage();

    expect(mounted.container.querySelector('button[aria-label="Open deck details"]')).toBeNull();
    expect(mounted.container.querySelector('button[aria-label="Open deck cards"]')).toBeNull();

    mounted.unmount();
  });

  test('renders unsaved changes confirmation modal from the editor controller', async () => {
    controller.discardChangesModalOpen.value = true;

    const mounted = await mountPage();
    const modal = mounted.container.querySelector<HTMLElement>('[data-testid="confirm-modal"]');
    const buttons = Array.from(mounted.container.querySelectorAll('button'));

    expect(modal?.textContent).toContain('Discard deck changes?');
    expect(modal?.textContent).toContain('Stay Here');
    expect(modal?.textContent).toContain('Discard Changes');

    buttons.find((button) => button.textContent === 'Stay Here')?.click();
    buttons.find((button) => button.textContent === 'Discard Changes')?.click();

    expect(controller.cancelDiscardChanges).toHaveBeenCalledTimes(1);
    expect(controller.confirmDiscardChanges).toHaveBeenCalledTimes(1);
    mounted.unmount();
  });

  test('does not change the save button label during autosync saves', async () => {
    controller.saving.value = true;
    controller.manualSaving.value = false;

    const mounted = await mountPage();
    const saveButton = mounted.container.querySelector<HTMLButtonElement>('button[aria-label="Save deck"]');

    expect(saveButton).toBeDefined();
    expect(saveButton?.disabled).toBe(false);
    expect(saveButton?.textContent).toBe('Save');
    mounted.unmount();
  });

  test('keeps the short save label while a manual save is loading', async () => {
    controller.manualSaving.value = true;

    const mounted = await mountPage();
    const saveButton = mounted.container.querySelector<HTMLButtonElement>('button[aria-label="Saving deck"]');

    expect(saveButton?.disabled).toBe(true);
    expect(saveButton?.textContent).toBe('Save');
    expect(saveButton?.querySelector('svg')?.classList.contains('animate-spin')).toBe(true);
    mounted.unmount();
  });
});
