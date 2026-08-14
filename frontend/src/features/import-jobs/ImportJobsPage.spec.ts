import { computed, createApp, h, ref } from 'vue';
import { createMemoryHistory, createRouter, RouterView } from 'vue-router';
import { createPinia } from 'pinia';
import { afterEach, describe, expect, test, vi } from 'vitest';
import ImportJobsPage from '@/features/import-jobs/ImportJobsPage.vue';
import { useImportJobsController } from '@/features/import-jobs/composables/useImportJobsController';
import type { ImportCreateState } from '@/features/import-jobs/composables/useImportJobsController';
import { useAuthStore } from '@/domain/session/store';

vi.mock('@/features/import-jobs/composables/useImportJobsController', () => ({
  useImportJobsController: vi.fn(),
}));

const mockedUseImportJobsController = vi.mocked(useImportJobsController);

describe('ImportJobsPage', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  test('renders flat setup and activity columns separated by a responsive divider', async () => {
    const createJobFromPicker = vi.fn();
    const unresolvedCreateAttempt = ref(false);
    const createState = ref<ImportCreateState>({ phase: 'idle' });
    mockedUseImportJobsController.mockReturnValue({
      pickerTemplateId: ref('mtg-like-v1'),
      cardPool: ref('player'),
      cardRoleMode: ref<'automatic' | 'override'>('override'),
      cardRoleOverride: ref([]),
      cardFactionMode: ref<'automatic' | 'override'>('override'),
      cardFactionOverride: ref([]),
      creationKey: ref('f1e10412-e8e8-49cb-9717-a24d2eec38c1'),
      contentVersionBase: ref('16.2'),
      contentVersionDescription: ref('Current release.'),
      currentContentVersion: ref({
        id: 'version-1',
        version_number: '16.2.0',
        base_version: '16.2',
        description: 'Current release.',
      }),
      pickedFiles: ref([new File(['image'], 'card.png', { type: 'image/png' })]),
      fileInputKey: ref(0),
      formErrorMessage: ref(''),
      activityErrorMessage: computed(() => ''),
      activeJobs: ref([]),
      recentJobs: computed(() => []),
      formLoaded: ref(true),
      currentContentVersionLoaded: ref(true),
      activeJobsLoaded: ref(true),
      historyLoaded: ref(true),
      activeJobsRefreshing: ref(false),
      historyRefreshing: ref(false),
      isRefreshing: computed(() => false),
      creatingJob: ref(false),
      cancellingJobIds: ref(new Set<string>()),
      lastRefreshedAt: ref('10:05:00'),
      templates: ref([
        {
          id: 'template-1',
          key: 'mtg-like-v1',
          label: 'Default card',
          definition_json: '{}',
          inferred_card_roles: [],
          inferred_card_factions: [],
        },
      ]),
      selectedJobDetail: ref(null),
      detailLoading: ref(false),
      queuedCount: computed(() => 0),
      runningCount: computed(() => 0),
      cancelingCount: computed(() => 0),
      contentVersionBaseError: computed(() => ''),
      hasValidVersionInput: computed(() => true),
      submitButtonLabel: computed(() => 'Update Version'),
      formLocked: computed(() => false),
      hasUnresolvedCreateAttempt: computed(() => unresolvedCreateAttempt.value),
      createState,
      refreshActivity: vi.fn(),
      createJobFromPicker,
      cancelJob: vi.fn(),
      viewJobDetail: vi.fn(),
      closeJobDetail: vi.fn(),
      setPickedFiles: vi.fn(),
      setCardPool: vi.fn(),
      clearPickedFiles: vi.fn(),
      abandonPendingAttempt: vi.fn(),
      pollJobs: vi.fn(),
      canCancel: vi.fn(),
      progressPercent: vi.fn(),
      recentProgressPercent: vi.fn(),
      statusClass: vi.fn(),
      progressClass: vi.fn(),
      formatTimestamp: vi.fn(),
    });
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/operations', component: ImportJobsPage },
        { path: '/other', component: { template: '<div />' } },
      ],
    });
    await router.push('/operations');
    await router.isReady();
    const host = document.createElement('div');
    document.body.appendChild(host);
    const app = createApp({ render: () => h(RouterView) });
    const pinia = createPinia();
    const auth = useAuthStore(pinia);
    auth.$patch({
      initialized: true,
      user: {
        authenticated: true,
        id: 'staff-1',
        username: 'staff',
        is_staff: true,
        can_access_admin: true,
        accessible_card_pools: ['player', 'evil', 'neutral'],
      },
    });
    app.use(pinia);
    app.use(router);
    app.mount(host);

    const layout = host.querySelector('.app-page-layout-one');
    const main = layout?.querySelector('.app-page-layout-main');
    const workspace = main?.children[0];
    const activityWrapper = workspace?.children[1];
    const form = workspace?.querySelector('form');
    const activityPanel = workspace?.querySelector('[data-testid="import-activity-panel"]');
    expect(layout).not.toBeNull();
    expect(main?.classList.contains('max-w-7xl')).toBe(true);
    expect(workspace?.className).toContain('xl:grid-cols-');
    expect(workspace?.children[0]?.querySelector('form')).toBe(form);
    expect(activityWrapper?.querySelector('[data-testid="import-activity-panel"]')).toBe(
      activityPanel,
    );
    expect(activityWrapper?.classList.contains('border-t')).toBe(true);
    expect(activityWrapper?.classList.contains('xl:border-l')).toBe(true);
    expect(form?.classList.contains('theme-card-frame')).toBe(false);
    expect(activityPanel?.classList.contains('theme-card-frame')).toBe(false);
    expect(host.querySelector('aside')).toBeNull();
    expect(
      Array.from(host.querySelectorAll('legend')).map((legend) => legend.textContent?.trim()),
    ).toEqual([
      'Card setup',
      'Card roles',
      'Card factions',
      'Content version',
      'Source images',
    ]);
    expect(
      Array.from(host.querySelectorAll('form > fieldset > legend')).every((legend) =>
        legend.classList.contains('pr-2'),
      ),
    ).toBe(true);
    expect(
      Array.from(host.querySelectorAll('fieldset > p.theme-section-muted')).every((description) =>
        description.classList.contains('mt-1'),
      ),
    ).toBe(true);
    expect(host.querySelectorAll('input[type="file"]')).toHaveLength(2);
    expect(host.textContent).not.toContain('Pick mode');
    expect(host.textContent).toContain('Card pool');
    expect(host.textContent).toContain('Automatic');
    expect(host.textContent).toContain('Location');
    const currentVersion = host.querySelector('[data-testid="current-content-version"]');
    const newVersionRow = host.querySelector('[data-testid="new-version-row"]');
    const versionInput = host.querySelector('#content-version-base');
    const versionLabel = versionInput?.closest('label');
    expect(currentVersion?.textContent).toContain('Current release');
    expect(currentVersion?.textContent).toContain('16.2.0');
    expect(currentVersion?.textContent).toContain('Current release.');
    expect(currentVersion?.classList.contains('theme-muted-panel')).toBe(true);
    expect(currentVersion?.classList.contains('md:col-span-2')).toBe(true);
    expect(
      currentVersion !== null
        && versionInput !== null
        && Boolean(
          currentVersion.compareDocumentPosition(versionInput)
            & Node.DOCUMENT_POSITION_FOLLOWING,
        ),
    ).toBe(true);
    expect(versionLabel?.textContent).toContain('New version');
    expect(newVersionRow?.className).toContain('16rem');
    expect(newVersionRow?.textContent).toContain('Patch number is automatic');
    expect(newVersionRow?.textContent).toContain(
      'Keep 16.2 to create the next available patch after 16.2.0.',
    );
    expect(versionInput?.getAttribute('aria-describedby')).toContain(
      'content-version-patch-help',
    );

    host
      .querySelector('form')
      ?.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    expect(createJobFromPicker).toHaveBeenCalledOnce();

    const confirmLeave = vi.spyOn(globalThis, 'confirm').mockReturnValue(false);
    unresolvedCreateAttempt.value = true;
    createState.value.phase = 'uncertain';
    await router.push('/other');
    expect(confirmLeave).toHaveBeenCalledOnce();
    expect(router.currentRoute.value.path).toBe('/operations');

    auth.$patch({ user: null });
    await router.push('/other');
    expect(router.currentRoute.value.path).toBe('/other');

    auth.$patch({
      user: {
        authenticated: true,
        id: 'staff-1',
        username: 'staff',
        is_staff: true,
        can_access_admin: true,
        accessible_card_pools: ['player', 'evil', 'neutral'],
      },
    });
    await router.push('/operations');

    confirmLeave.mockReturnValue(true);
    await router.push('/other');
    expect(router.currentRoute.value.path).toBe('/other');
    confirmLeave.mockRestore();

    app.unmount();
  });
});
