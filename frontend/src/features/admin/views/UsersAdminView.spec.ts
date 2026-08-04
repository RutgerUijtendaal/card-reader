import { createApp, nextTick, ref } from 'vue';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import UsersAdminView from './UsersAdminView.vue';

const mocks = vi.hoisted(() => ({
  developerEnabled: false,
  loadAccessRequests: vi.fn().mockResolvedValue(undefined),
  loadUsers: vi.fn().mockResolvedValue(undefined),
  setDeveloperAccess: vi.fn().mockResolvedValue(undefined),
  toastError: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock('@/domain/session/store', () => ({
  useAuthStore: () => ({ user: { is_superuser: false } }),
}));

vi.mock('vue-sonner', () => ({
  toast: {
    error: mocks.toastError,
    success: mocks.toastSuccess,
  },
}));

vi.mock('@/features/admin/composables/useManagedUsers', () => ({
  useManagedUsers: () => ({
    users: ref([
      {
        id: 'user-1',
        username: 'developer-candidate',
        is_active: true,
        is_staff: false,
        is_superuser: false,
        is_developer: mocks.developerEnabled,
        date_joined: '2026-08-04T10:00:00Z',
        last_login: null,
        last_active_at: null,
      },
    ]),
    unmanagedUsers: ref([]),
    includeInactive: ref(false),
    includeResolvedAccessRequests: ref(false),
    accessRequests: ref([]),
    loading: ref(false),
    loadingAccessRequests: ref(false),
    setupResponse: ref(null),
    loadUsers: mocks.loadUsers,
    loadAccessRequests: mocks.loadAccessRequests,
    createUser: vi.fn(),
    deactivateUser: vi.fn(),
    restoreUser: vi.fn(),
    resetPassword: vi.fn(),
    setDeveloperAccess: mocks.setDeveloperAccess,
    approveRequest: vi.fn(),
    declineRequest: vi.fn(),
  }),
}));

const mountView = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp(UsersAdminView);
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

describe('UsersAdminView developer access', () => {
  beforeEach(() => {
    mocks.developerEnabled = false;
    mocks.setDeveloperAccess.mockClear();
    mocks.toastSuccess.mockClear();
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('grants developer access to a managed user', async () => {
    const mounted = await mountView();
    const grantButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Grant developer access'),
    );

    expect(grantButton).toBeDefined();
    grantButton?.click();
    await nextTick();

    expect(mocks.setDeveloperAccess).toHaveBeenCalledWith('user-1', true);
    expect(mocks.toastSuccess).toHaveBeenCalledWith('Developer access granted.');
    mounted.unmount();
  });

  test('shows the role and removal action for developers', async () => {
    mocks.developerEnabled = true;
    const mounted = await mountView();

    expect(mounted.container.textContent).toContain('Developer');
    expect(mounted.container.textContent).toContain('Remove developer access');
    mounted.unmount();
  });
});
