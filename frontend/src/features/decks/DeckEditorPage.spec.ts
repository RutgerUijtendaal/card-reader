/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import DeckEditorPage from '@/features/decks/DeckEditorPage.vue';

const { controller } = vi.hoisted(() => {
  const refValue = <T,>(value: T) => ({ value, __v_isRef: true });

  return {
    controller: {
      deckId: refValue('deck-1'),
      isPublished: refValue(true),
      backLink: refValue('/my/decks'),
      backLabel: refValue('Back to My Decks'),
      editorMode: refValue<'hero' | 'details' | 'cards'>('cards'),
      isChangingHero: refValue(false),
      saving: refValue(false),
      manualSaving: refValue(false),
      isCreating: refValue(false),
      isMutationLocked: refValue(false),
      terminalNavigationPending: refValue(false),
      terminalNavigationInFlight: refValue(false),
      creationState: refValue<
        | { status: 'idle' }
        | { status: 'creating' }
        | { status: 'unknown'; reconciliation: 'checking' | 'awaiting-retry' }
      >({ status: 'idle' }),
      persistenceState: refValue({ status: 'synced' }),
      loading: refValue(false),
      hasUnsavedChanges: refValue(true),
      hasLocalDraft: refValue(false),
      localDraftPersistenceFailed: refValue(false),
      canAutosync: refValue(true),
      changeStatusLabel: refValue('Unsaved'),
      autosyncEnabled: refValue(false),
      discardChangesModalOpen: refValue(false),
      discardLocalDraftModalOpen: refValue(false),
      localDraftRecoveryModalOpen: refValue(false),
      recoveryActionPending: refValue(false),
      pendingLocalDraft: refValue<null | { savedAt: string }>(null),
      localDraftConflict: refValue<null | {
        kind: 'active-draft' | 'remote-deletion' | 'created-elsewhere';
      }>(null),
      localDraftConflictModalOpen: refValue(false),
      conflictActionsLocked: refValue(false),
      deckBuildingRules: refValue({
        mainboard_card_count: { min: 40, max: 60 },
        mana_type_count: { min: 10 },
      }),
      saveDeck: vi.fn(),
      openHero: vi.fn(),
      openDetails: vi.fn(),
      openCards: vi.fn(),
      confirmDiscardChanges: vi.fn(),
      cancelDiscardChanges: vi.fn(),
      requestDiscardLocalDraft: vi.fn(),
      confirmDiscardLocalDraft: vi.fn(),
      cancelDiscardLocalDraft: vi.fn(),
      resumeLocalDraft: vi.fn(),
      discardPendingLocalDraft: vi.fn(),
      loadStoredConflictDraft: vi.fn(),
      keepThisConflictDraft: vi.fn(),
      discardThisConflictedTab: vi.fn(),
      openCreatedConflictDeck: vi.fn(),
      keepConflictAsNewDraft: vi.fn(),
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
          slots.center?.(),
          slots.actions?.(),
        ]);
    },
  }),
}));

vi.mock('@/shared/components/app/AppPageLayout.vue', () => ({
  default: defineComponent({
    setup(_, { attrs, slots }) {
      return () =>
        h('main', { ...attrs, 'data-testid': 'builder-layout' }, [
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

vi.mock('@/features/decks/components/DeckDraftRecoveryModal.vue', () => ({
  default: defineComponent({
    props: {
      open: { type: Boolean, required: true },
    },
    setup(props, { emit }) {
      return () => props.open
        ? h('section', { 'data-testid': 'draft-recovery-modal' }, [
            h('button', { onClick: () => emit('discard') }, 'Discard Draft'),
            h('button', { onClick: () => emit('resume') }, 'Resume Draft'),
          ])
        : null;
    },
  }),
}));

vi.mock('@/features/decks/components/DeckDraftConflictModal.vue', () => ({
  default: defineComponent({
    props: {
      open: { type: Boolean, required: true },
      kind: { type: String, default: undefined },
      busy: { type: Boolean, default: false },
    },
    setup(props, { emit }) {
      return () => props.open
        ? h('section', { 'data-testid': 'draft-conflict-modal' }, [
            h('span', props.kind),
            h('button', { disabled: props.busy, onClick: () => emit('useStored') }, 'Use stored'),
            h('button', { disabled: props.busy, onClick: () => emit('keepLocal') }, 'Keep local'),
          ])
        : null;
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
    controller.isPublished.value = true;
    controller.editorMode.value = 'cards';
    controller.isChangingHero.value = false;
    controller.loading.value = false;
    controller.saving.value = false;
    controller.manualSaving.value = false;
    controller.isCreating.value = false;
    controller.isMutationLocked.value = false;
    controller.terminalNavigationPending.value = false;
    controller.terminalNavigationInFlight.value = false;
    controller.creationState.value = { status: 'idle' };
    controller.changeStatusLabel.value = 'Unsaved';
    controller.hasUnsavedChanges.value = true;
    controller.hasLocalDraft.value = false;
    controller.localDraftPersistenceFailed.value = false;
    controller.canAutosync.value = true;
    controller.autosyncEnabled.value = false;
    controller.discardChangesModalOpen.value = false;
    controller.discardLocalDraftModalOpen.value = false;
    controller.localDraftRecoveryModalOpen.value = false;
    controller.pendingLocalDraft.value = null;
    controller.localDraftConflict.value = null;
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
    controller.isPublished.value = false;
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
    controller.isPublished.value = true;
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

  test('shows Hero, Details, Cards, and Create for an unpublished draft', async () => {
    controller.deckId.value = '';
    controller.isPublished.value = false;
    controller.editorMode.value = 'cards';
    controller.canAutosync.value = false;
    controller.changeStatusLabel.value = 'Local Draft';

    const mounted = await mountPage();
    const heroTab = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Open deck hero"]',
    );
    const createButton = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Create deck"]',
    );
    const autosyncCheckbox = mounted.container.querySelector<HTMLInputElement>(
      'input[type="checkbox"]',
    );

    expect(heroTab).not.toBeNull();
    expect(mounted.container.querySelector('button[aria-label="Open deck details"]')).not.toBeNull();
    expect(mounted.container.querySelector('button[aria-label="Open deck cards"]')).not.toBeNull();
    expect(mounted.container.querySelectorAll('.deck-editor-header-divider')).toHaveLength(1);
    expect(
      mounted.container.querySelector('nav[aria-label="Deck editor sections"]'),
    ).not.toBeNull();
    expect(createButton?.textContent).toBe('Create');
    expect(autosyncCheckbox?.disabled).toBe(true);
    expect(mounted.container.textContent).toContain('Autosync after creation');

    heroTab?.click();
    createButton?.click();
    await nextTick();

    expect(controller.openHero).toHaveBeenCalledTimes(1);
    expect(controller.saveDeck).toHaveBeenCalledTimes(1);
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

  test('warns when leaving would discard an unpersisted local draft', async () => {
    controller.deckId.value = '';
    controller.isPublished.value = false;
    controller.localDraftPersistenceFailed.value = true;
    controller.discardChangesModalOpen.value = true;

    const mounted = await mountPage();
    const modal = mounted.container.querySelector<HTMLElement>('[data-testid="confirm-modal"]');

    expect(modal?.textContent).toContain('could not be saved in this browser');
    expect(modal?.textContent).toContain('Discard & Leave');

    mounted.unmount();
  });

  test('disables deck editing controls during initial creation', async () => {
    controller.deckId.value = '';
    controller.isPublished.value = false;
    controller.isCreating.value = true;
    controller.isMutationLocked.value = true;
    controller.creationState.value = { status: 'creating' };
    controller.saving.value = true;
    controller.manualSaving.value = true;
    controller.hasLocalDraft.value = true;

    const mounted = await mountPage();
    const page = mounted.container.querySelector('section');
    const layout = mounted.container.querySelector<HTMLElement>('[data-testid="builder-layout"]');

    expect(layout?.hasAttribute('inert')).toBe(true);
    expect(page?.getAttribute('aria-busy')).toBe('true');
    expect(
      mounted.container.querySelector<HTMLButtonElement>('button[aria-label="Open deck hero"]')?.disabled,
    ).toBe(true);
    expect(
      mounted.container.querySelector<HTMLButtonElement>('button[aria-label="Open deck details"]')?.disabled,
    ).toBe(true);
    expect(
      mounted.container.querySelector<HTMLButtonElement>('button[aria-label="Open deck cards"]')?.disabled,
    ).toBe(true);
    expect(
      mounted.container.querySelector<HTMLButtonElement>('button[aria-label="Discard local draft"]')?.disabled,
    ).toBe(true);

    mounted.unmount();
  });

  test('offers Retry with the editor locked when creation is unconfirmed', async () => {
    controller.deckId.value = '';
    controller.isPublished.value = false;
    controller.isMutationLocked.value = true;
    controller.creationState.value = { status: 'unknown', reconciliation: 'awaiting-retry' };

    const mounted = await mountPage();
    const retryButton = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Retry deck creation"]',
    );

    expect(retryButton?.textContent).toBe('Retry');
    expect(retryButton?.disabled).toBe(false);
    retryButton?.click();
    expect(controller.saveDeck).toHaveBeenCalledTimes(1);

    mounted.unmount();
  });

  test('offers Continue while a confirmed outcome is waiting for navigation', async () => {
    controller.deckId.value = '';
    controller.isPublished.value = false;
    controller.isMutationLocked.value = true;
    controller.terminalNavigationPending.value = true;

    const mounted = await mountPage();
    const continueButton = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Continue after confirmed deck outcome"]',
    );

    expect(continueButton?.textContent).toBe('Continue');
    expect(continueButton?.disabled).toBe(false);
    continueButton?.click();
    expect(controller.saveDeck).toHaveBeenCalledTimes(1);

    mounted.unmount();
  });

  test('disables Continue while terminal navigation is in flight', async () => {
    controller.deckId.value = '';
    controller.isPublished.value = false;
    controller.isMutationLocked.value = true;
    controller.terminalNavigationPending.value = true;
    controller.terminalNavigationInFlight.value = true;

    const mounted = await mountPage();
    const continueButton = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Continue after confirmed deck outcome"]',
    );

    expect(continueButton?.disabled).toBe(true);
    expect(continueButton?.querySelector('svg')?.classList.contains('animate-spin')).toBe(true);

    mounted.unmount();
  });

  test('offers resume and discard when a local draft is recovered', async () => {
    controller.localDraftRecoveryModalOpen.value = true;
    controller.pendingLocalDraft.value = { savedAt: '2026-08-09T10:00:00Z' };

    const mounted = await mountPage();
    const modal = mounted.container.querySelector<HTMLElement>(
      '[data-testid="draft-recovery-modal"]',
    );
    const buttons = Array.from(modal?.querySelectorAll('button') ?? []);

    buttons.find((button) => button.textContent === 'Resume Draft')?.click();
    buttons.find((button) => button.textContent === 'Discard Draft')?.click();

    expect(controller.resumeLocalDraft).toHaveBeenCalledTimes(1);
    expect(controller.discardPendingLocalDraft).toHaveBeenCalledTimes(1);
    mounted.unmount();
  });

  test('shows a draft conflict only after recovery or creation locking finishes', async () => {
    controller.localDraftConflict.value = { kind: 'active-draft' };
    controller.localDraftConflictModalOpen.value = false;
    const mounted = await mountPage();

    expect(mounted.container.querySelector('[data-testid="draft-conflict-modal"]')).toBeNull();
    mounted.unmount();

    controller.localDraftConflictModalOpen.value = true;
    const remounted = await mountPage();

    expect(remounted.container.querySelector('[data-testid="draft-conflict-modal"]')).not.toBeNull();
    remounted.unmount();
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
