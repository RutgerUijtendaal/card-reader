/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardDetailPage from '@/features/card-detail/CardDetailPage.vue';
import CardPublicDetailPage from '@/features/card-detail/CardPublicDetailPage.vue';

const { editorState, publicState, routerPushMock, workspaceState } = vi.hoisted(() => {
  const refValue = <T,>(value: T) => ({ value, __v_isRef: true });
  const route = {
    params: { id: 'card-1' },
    path: '/cards/card-1',
    query: {},
  };
  const form = {
    name: '',
    type_line: '',
    mana_cost: '',
    attack: '',
    health: '',
    rules_text: '',
    card_pool: 'player' as const, card_roles: [],
    deck_building_config: '{}',
    lifecycle_status: 'active',
    keyword_ids: [],
    tag_ids: [],
    type_ids: [],
    additional_symbol_ids: [],
  };
  return {
    routerPushMock: vi.fn(),
    workspaceState: {
      activePool: 'player' as 'player' | 'evil' | 'neutral',
    },
    editorState: {
      card: refValue<unknown | null>(null),
      versions: refValue([]),
      selectedVersionId: refValue(''),
      symbolByKey: refValue({}),
      hasGalleryContext: refValue(false),
      previousCardId: refValue<string | null>(null),
      nextCardId: refValue<string | null>(null),
      hasMoreResults: refValue(false),
      isLoadingMoreCards: refValue(false),
      positionLabel: refValue(''),
      reparseTemplates: refValue([]),
      reparseTemplateId: refValue(''),
      isSaving: refValue(false),
      isLoadingInitial: refValue(false),
      isQueuingReparse: refValue(false),
      promotingVersionId: refValue<string | null>(null),
      saveMessage: refValue(''),
      deckBuildingConfigExample: refValue('{}'),
      form,
      selectedVersion: refValue<unknown | null>(null),
      isBusy: refValue(false),
      ruleTextUnknownSymbolKeys: refValue([]),
      rulesTextSymbols: refValue([]),
      backButtonLabel: refValue('Back to Cards'),
      reviewFocusPropertyKey: refValue(''),
      route,
      goToPreviousCard: vi.fn(),
      goToNextCard: vi.fn(),
      loadCard: vi.fn(),
      selectVersion: vi.fn(),
      saveCardEdits: vi.fn(),
      saveVersionEdits: vi.fn(),
      restoreField: vi.fn(),
      unlockField: vi.fn(),
      restoreMetadataGroup: vi.fn(),
      unlockMetadataGroup: vi.fn(),
      resetWholeCardToAuto: vi.fn(),
      queueLatestCardReparse: vi.fn(),
      promoteVersion: vi.fn(),
      fieldSource: vi.fn(() => 'auto'),
      metadataSource: vi.fn(() => 'auto'),
      fieldSourceLabel: vi.fn(() => 'Auto'),
      metadataSourceLabel: vi.fn(() => 'Auto'),
      fieldHasParsedSuggestion: vi.fn(() => false),
      formatParsedFieldValue: vi.fn(() => ''),
      metadataHasParsedSuggestion: vi.fn(() => false),
      metadataSearch: {
        keywords: '',
        tags: '',
        types: '',
        symbols: '',
      },
      selectedIds: vi.fn(() => []),
      parsedMetadataLabels: vi.fn(() => []),
      optionsForGroup: vi.fn(() => []),
      setMetadataSearch: vi.fn(),
      toggleMetadataSelection: vi.fn(),
      toggleAdditionalSymbol: vi.fn(),
      toAbsoluteApiUrl: vi.fn((value: string) => value),
      formatDate: vi.fn((value: string) => value),
    },
    publicState: {
      card: refValue<unknown | null>(null),
      versions: refValue([]),
      selectedVersionId: refValue(''),
      selectedVersion: refValue<unknown | null>(null),
      symbolByKey: refValue({}),
      isLoadingInitial: refValue(false),
      canEdit: refValue(false),
      backButtonLabel: refValue('Back to Cards'),
      hasGalleryContext: refValue(false),
      previousCardId: refValue<string | null>(null),
      nextCardId: refValue<string | null>(null),
      hasMoreResults: refValue(false),
      isLoadingMoreCards: refValue(false),
      positionLabel: refValue(''),
      loadCard: vi.fn(),
      goToPreviousCard: vi.fn(),
      goToNextCard: vi.fn(),
      openEditor: vi.fn(),
      selectVersion: vi.fn(),
      toAbsoluteApiUrl: vi.fn((value: string) => value),
      formatDate: vi.fn((value: string) => value),
    },
  };
});

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { id: 'card-1' },
    path: '/cards/card-1',
    query: {},
  }),
  useRouter: () => ({
    push: routerPushMock,
  }),
}));

vi.mock('@/features/card-detail/composables/useCardDetailState', () => ({
  useCardDetailState: () => editorState,
}));

vi.mock('@/features/card-detail/composables/useCardPublicDetailState', () => ({
  useCardPublicDetailState: () => publicState,
}));

vi.mock('@/domain/session/store', () => ({
  useAuthStore: () => ({
    authenticated: true,
    canAccessStaffRoutes: true,
    user: { id: 'user-1' },
  }),
}));

vi.mock('@/domain/cards/cardPoolWorkspace', () => ({
  useCardPoolWorkspaceStore: () => workspaceState,
}));

vi.mock('@/shared/api/client', () => ({
  api: {
    post: vi.fn(),
  },
}));

vi.mock('vue-sonner', () => ({
  toast: {
    success: vi.fn(),
  },
}));

vi.mock('@/domain/review/composables/useReviewSummary', () => ({
  useReviewSummary: () => ({
    incrementOpenParseFlagItemCount: vi.fn(),
  }),
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
          slots.titleMeta?.(),
          slots.details?.(),
          slots.actions?.(),
        ]);
    },
  }),
}));

vi.mock('@/domain/cards/components/CardResultPager.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('nav', { 'data-testid': 'card-detail-pager' }, 'Pager');
    },
  }),
}));

vi.mock('@/domain/cards/components/CardVersionOverviewPane.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('section', { 'data-testid': 'card-version-overview' }, 'Overview');
    },
  }),
}));

vi.mock('@/features/card-detail/components/CardVersionSelectorGrid.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('section', { 'data-testid': 'card-version-selector' }, 'Printings');
    },
  }),
}));

vi.mock('@/features/card-detail/components/CardVersionEditorPane.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('aside', { 'data-testid': 'card-version-editor' }, 'Editor');
    },
  }),
}));

vi.mock('@/domain/card-deck-references/components/CardDeckReferencesPanel.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('aside', { 'data-testid': 'card-deck-references' }, 'Deck references');
    },
  }),
}));

vi.mock('@/features/card-detail/components/CardVersionParseFlagModal.vue', () => ({
  default: defineComponent({
    setup() {
      return () => h('div', { 'data-testid': 'parse-flag-modal' });
    },
  }),
}));

const resetState = (): void => {
  const card = {
    id: 'card-1',
    label: 'Loaded Card',
    name: 'Loaded Card',
    card_groups: [],
    deck_references: [],
    card_pool: 'player',
    card_roles: [],
    card_factions: [],
  };
  editorState.card.value = card;
  editorState.selectedVersion.value = null;
  editorState.isLoadingInitial.value = false;
  editorState.hasGalleryContext.value = false;
  editorState.loadCard.mockClear();
  routerPushMock.mockClear();
  publicState.card.value = card;
  publicState.selectedVersion.value = null;
  publicState.isLoadingInitial.value = false;
  publicState.hasGalleryContext.value = false;
  publicState.canEdit.value = false;
  publicState.loadCard.mockClear();
  publicState.openEditor.mockClear();
  workspaceState.activePool = 'player';
};

const mountPage = async (page: typeof CardDetailPage | typeof CardPublicDetailPage) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp(page);
  app.component(
    'RouterLink',
    defineComponent({
      setup(_, { slots }) {
        return () => h('a', slots.default?.());
      },
    }),
  );
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

describe('CardDetailPage loading state', () => {
  afterEach(() => {
    resetState();
    document.body.innerHTML = '';
  });

  test('renders the editor-shaped skeleton during initial load', async () => {
    resetState();
    editorState.isLoadingInitial.value = true;

    const mounted = await mountPage(CardDetailPage);

    expect(mounted.container.querySelector('[aria-label="Loading card detail"]')).not.toBeNull();
    expect(mounted.container.textContent).not.toContain('No printings found.');
    expect(mounted.container.querySelector('[data-testid="card-version-editor"]')).toBeNull();
    expect(mounted.container.querySelector('.card-detail-loading-pager')).toBeNull();
    expect(editorState.loadCard).toHaveBeenCalledTimes(1);

    mounted.unmount();
  });

  test('renders the pager skeleton during initial load when gallery context exists', async () => {
    resetState();
    editorState.isLoadingInitial.value = true;
    editorState.hasGalleryContext.value = true;

    const mounted = await mountPage(CardDetailPage);

    expect(mounted.container.querySelector('.card-detail-loading-pager')).not.toBeNull();
    expect(mounted.container.querySelectorAll('.card-detail-loading-button')).toHaveLength(2);

    mounted.unmount();
  });

  test('renders the empty state only after loading completes', async () => {
    resetState();

    const mounted = await mountPage(CardDetailPage);

    expect(mounted.container.querySelector('[aria-label="Loading card detail"]')).toBeNull();
    expect(mounted.container.textContent).toContain('No printings found.');

    mounted.unmount();
  });

  test('renders detail content when a version is selected', async () => {
    resetState();
    editorState.selectedVersion.value = { id: 'card-1', version_id: 'version-1', name: 'Loaded Card' };

    const mounted = await mountPage(CardDetailPage);

    expect(mounted.container.querySelector('[data-testid="card-version-overview"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="card-version-selector"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="card-version-editor"]')).not.toBeNull();
    expect(mounted.container.textContent).not.toContain('No printings found.');

    mounted.unmount();
  });

  test('keeps the full Merge/Rename header label with its contextual accessible name', async () => {
    resetState();

    const mounted = await mountPage(CardDetailPage);
    const action = mounted.container.querySelector<HTMLButtonElement>('button[aria-label="Merge or rename card"]');

    expect(action?.textContent).toBe('Merge/Rename');
    action?.click();
    expect(routerPushMock).toHaveBeenCalledTimes(1);

    mounted.unmount();
  });
});

describe('CardPublicDetailPage loading state', () => {
  afterEach(() => {
    resetState();
    document.body.innerHTML = '';
  });

  test('renders the public-shaped skeleton during initial load', async () => {
    resetState();
    publicState.isLoadingInitial.value = true;

    const mounted = await mountPage(CardPublicDetailPage);

    expect(mounted.container.querySelector('[aria-label="Loading card detail"]')).not.toBeNull();
    expect(mounted.container.textContent).not.toContain('No printings found.');
    expect(mounted.container.querySelector('[data-testid="card-deck-references"]')).toBeNull();
    expect(mounted.container.querySelector('.card-detail-loading-pager')).toBeNull();
    expect(publicState.loadCard).toHaveBeenCalledTimes(1);

    mounted.unmount();
  });

  test('renders the pager skeleton during public initial load when gallery context exists', async () => {
    resetState();
    publicState.isLoadingInitial.value = true;
    publicState.hasGalleryContext.value = true;

    const mounted = await mountPage(CardPublicDetailPage);

    expect(mounted.container.querySelector('.card-detail-loading-pager')).not.toBeNull();
    expect(mounted.container.querySelectorAll('.card-detail-loading-button')).toHaveLength(2);

    mounted.unmount();
  });

  test('renders the empty state only after loading completes', async () => {
    resetState();

    const mounted = await mountPage(CardPublicDetailPage);

    expect(mounted.container.querySelector('[aria-label="Loading card detail"]')).toBeNull();
    expect(mounted.container.textContent).toContain('No printings found.');

    mounted.unmount();
  });

  test('renders public detail content when a version is selected', async () => {
    resetState();
    publicState.selectedVersion.value = { id: 'card-1', version_id: 'version-1', name: 'Loaded Card' };

    const mounted = await mountPage(CardPublicDetailPage);

    expect(mounted.container.querySelector('[data-testid="card-version-overview"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="card-version-selector"]')).not.toBeNull();
    expect(mounted.container.querySelector('[data-testid="card-deck-references"]')).not.toBeNull();
    expect(mounted.container.textContent).not.toContain('No printings found.');

    mounted.unmount();
  });

  test('labels a card whose pool differs from the active workspace', async () => {
    resetState();
    workspaceState.activePool = 'evil';

    const mounted = await mountPage(CardPublicDetailPage);
    const badge = mounted.container.querySelector('[data-testid="cross-pool-card-badge"]');

    expect(badge?.textContent?.trim()).toBe('Player');
    expect(badge?.getAttribute('aria-label')).toBe('Player card');

    mounted.unmount();
  });

  test('does not add a redundant pool label inside the matching workspace', async () => {
    resetState();

    const mounted = await mountPage(CardPublicDetailPage);

    expect(mounted.container.querySelector('[data-testid="cross-pool-card-badge"]')).toBeNull();

    mounted.unmount();
  });

  test('renders the compact card edit action for authorized users', async () => {
    resetState();
    publicState.canEdit.value = true;

    const mounted = await mountPage(CardPublicDetailPage);
    const action = mounted.container.querySelector<HTMLButtonElement>('button[aria-label="Edit card"]');

    expect(action?.textContent).toBe('Edit');
    action?.click();
    expect(publicState.openEditor).toHaveBeenCalledTimes(1);

    mounted.unmount();
  });
});
