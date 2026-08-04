import { createApp, nextTick } from 'vue';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import AdminPage from '@/features/admin/AdminPage.vue';

const { authState, pendingCount, replaceAdminQueryMock, routeState } = vi.hoisted(() => ({
  authState: {
    canAccessMaintenance: true,
    canManageUsers: true,
  },
  pendingCount: { value: 2, __v_isRef: true },
  replaceAdminQueryMock: vi.fn(),
  routeState: { query: {} },
}));

vi.mock('@/domain/session/store', () => ({
  useAuthStore: () => authState,
}));

vi.mock('@/domain/access-requests/composables/useAccessRequestSummary', () => ({
  useAccessRequestSummary: () => ({ pendingAccessRequestCount: pendingCount }),
}));

vi.mock('@/features/admin/composables/useAdminRouteSync', () => ({
  useAdminRouteSync: () => ({
    route: routeState,
    replaceAdminQuery: replaceAdminQueryMock,
  }),
}));

vi.mock('@/features/admin/views/MaintenanceAdminView.vue', () => ({
  default: { template: '<div data-testid="MaintenanceAdminView" />' },
}));
vi.mock('@/features/admin/views/CatalogAdminView.vue', () => ({
  default: { template: '<div data-testid="CatalogAdminView" />' },
}));
vi.mock('@/features/admin/views/CardGroupsAdminView.vue', () => ({
  default: { template: '<div data-testid="CardGroupsAdminView" />' },
}));
vi.mock('@/features/admin/views/CardBacksAdminView.vue', () => ({
  default: { template: '<div data-testid="CardBacksAdminView" />' },
}));
vi.mock('@/features/admin/views/CardMergesAdminView.vue', () => ({
  default: { template: '<div data-testid="CardMergesAdminView" />' },
}));
vi.mock('@/features/admin/views/ContentVersionsAdminView.vue', () => ({
  default: { template: '<div data-testid="ContentVersionsAdminView" />' },
}));
vi.mock('@/features/admin/views/TemplatesAdminView.vue', () => ({
  default: { template: '<div data-testid="TemplatesAdminView" />' },
}));
vi.mock('@/features/admin/views/UsersAdminView.vue', () => ({
  default: { template: '<div data-testid="UsersAdminView" />' },
}));

const mountPage = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp(AdminPage);
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

describe('AdminPage header tabs', () => {
  beforeEach(() => {
    authState.canAccessMaintenance = true;
    authState.canManageUsers = true;
    pendingCount.value = 2;
    replaceAdminQueryMock.mockClear();
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('uses shared labelled actions, active state, permissions, and the pending-user badge', async () => {
    const mounted = await mountPage();
    const actions = Array.from(mounted.container.querySelectorAll<HTMLButtonElement>('.app-header-action'));

    expect(actions.map((action) => action.textContent?.trim())).toEqual([
      'Catalog',
      'Templates',
      'Versions',
      'Backs',
      'Groups',
      'Merges',
      'Users2',
      'System',
    ]);
    expect(actions.every((action) => action.classList.contains('h-10'))).toBe(true);
    expect(actions.every((action) => action.querySelector('svg')?.classList.contains('h-4'))).toBe(true);
    expect(mounted.container.querySelector('[aria-label="Catalog"]')?.getAttribute('aria-pressed')).toBe('true');
    expect(mounted.container.querySelector('[aria-label="Card backs"]')?.textContent).toBe('Backs');
    expect(mounted.container.querySelector('[aria-label="Maintenance"]')?.textContent).toBe('System');

    const groupsAction = mounted.container.querySelector<HTMLButtonElement>('[aria-label="Card groups"]');
    groupsAction?.click();
    await nextTick();
    expect(groupsAction?.getAttribute('aria-pressed')).toBe('true');
    expect(replaceAdminQueryMock).toHaveBeenCalledWith({ tab: 'card-groups' });

    mounted.unmount();
  });

  test('preserves permission-gated tabs', async () => {
    authState.canAccessMaintenance = false;
    authState.canManageUsers = false;
    const mounted = await mountPage();

    expect(mounted.container.querySelector('[aria-label="Users"]')).toBeNull();
    expect(mounted.container.querySelector('[aria-label="Maintenance"]')).toBeNull();

    mounted.unmount();
  });
});
