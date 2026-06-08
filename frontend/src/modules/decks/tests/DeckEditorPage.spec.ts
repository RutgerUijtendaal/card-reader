/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import DeckEditorPage from '@/modules/decks/DeckEditorPage.vue';

const { controller } = vi.hoisted(() => {
  const refValue = <T,>(value: T) => ({ value, __v_isRef: true });

  return {
    controller: {
      deckId: refValue('deck-1'),
      backLink: refValue('/my/decks'),
      backLabel: refValue('Back to My Decks'),
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
      confirmDiscardChanges: vi.fn(),
      cancelDiscardChanges: vi.fn(),
      deck: {
        isSetupStep: refValue(false),
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

vi.mock('@/modules/decks/composables/useDeckEditor', () => ({
  useDeckEditor: () => controller,
}));

vi.mock('@/components/app/AppPageHeader.vue', () => ({
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

vi.mock('@/components/app/AppPageLayout.vue', () => ({
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

vi.mock('@/components/InfoTooltip.vue', () => ({
  default: defineComponent({
    setup(_, { slots }) {
      return () => h('span', slots.default?.());
    },
  }),
}));

vi.mock('@/components/modals/ConfirmModal.vue', () => ({
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

vi.mock('@/modules/decks/components/DeckBuilderFiltersPanel.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('aside', 'Filters');
    },
  }),
}));

vi.mock('@/modules/decks/components/DeckBuilderGallery.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('section', { 'data-testid': 'builder-gallery' }, 'Gallery');
    },
  }),
}));

vi.mock('@/modules/decks/components/DeckBuilderSummaryPanel.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('aside', 'Summary');
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
    controller.deck.isSetupStep.value = false;
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

    mounted.unmount();
  });

  test('keeps the builder status bar hidden during setup', async () => {
    controller.deck.isSetupStep.value = true;

    const mounted = await mountPage();

    expect(mounted.container.querySelector('[aria-label="Deck builder status"]')).toBeNull();
    expect(mounted.container.querySelector('[data-testid="builder-layout"]')).not.toBeNull();

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
    const saveButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Save Deck'),
    );

    expect(saveButton).toBeDefined();
    expect(saveButton?.disabled).toBe(false);
    expect(saveButton?.textContent).toContain('Save Deck');
    expect(saveButton?.textContent).not.toContain('Saving...');
    mounted.unmount();
  });
});
