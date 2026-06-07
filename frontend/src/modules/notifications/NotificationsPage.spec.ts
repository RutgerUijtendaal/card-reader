import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import NotificationsPage from '@/modules/notifications/NotificationsPage.vue';
import type { NotificationPage, UserNotification } from '@/modules/notifications/types';

const { fetchNotifications, markAllNotificationsRead, setNotificationReadState, unreadNotificationCount } = vi.hoisted(() => ({
  fetchNotifications: vi.fn(),
  markAllNotificationsRead: vi.fn(),
  setNotificationReadState: vi.fn(),
  unreadNotificationCount: { value: 1, __v_isRef: true },
}));

vi.mock('@/modules/notifications/api', () => ({
  buildNotificationSearchParams: (status: string, page: number, pageSize: number) => {
    const params = new URLSearchParams();
    params.set('status', status);
    params.set('page', String(page));
    params.set('page_size', String(pageSize));
    return params;
  },
  fetchNotifications,
  markAllNotificationsRead,
  setNotificationReadState,
}));

vi.mock('@/composables/useNotificationSummary', () => ({
  useNotificationSummary: () => ({
    unreadNotificationCount,
    loadNotificationSummary: vi.fn(),
    setUnreadNotificationCount: (count: number) => {
      unreadNotificationCount.value = count;
    },
  }),
}));

const notification = (overrides: Partial<UserNotification> = {}): UserNotification => ({
  id: 'notification-1',
  event_type: 'deck.card_changed',
  subject_type: 'deck_card',
  subject_id: 'deck-1:card-1',
  target_url: '/my/decks/deck-1',
  title: 'Card changed in Deck',
  message: 'A card changed.',
  metadata: {},
  event_count: 2,
  read_at: null,
  created_at: '2026-06-07T10:00:00Z',
  updated_at: '2026-06-07T10:00:00Z',
  last_event_at: '2026-06-07T10:00:00Z',
  actor: null,
  ...overrides,
});

const pagePayload = (results: UserNotification[]): NotificationPage => ({
  count: results.length,
  next_page: null,
  previous_page: null,
  page: 1,
  page_size: 25,
  results,
});

const flushPromises = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
};

const mountView = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/notifications', component: NotificationsPage },
      { path: '/my/decks/:id', component: { template: '<div />' } },
    ],
  });
  await router.push('/notifications');
  await router.isReady();
  const app = createApp(NotificationsPage);
  app.use(router);
  app.mount(container);
  await flushPromises();
  await nextTick();

  return {
    container,
    router,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('NotificationsPage', () => {
  afterEach(() => {
    vi.clearAllMocks();
    unreadNotificationCount.value = 1;
    document.body.innerHTML = '';
  });

  test('renders notifications and marks a row read', async () => {
    const row = notification();
    fetchNotifications.mockResolvedValue(pagePayload([row]));
    setNotificationReadState.mockResolvedValue(notification({ read_at: '2026-06-07T10:01:00Z' }));

    const mounted = await mountView();
    const button = Array.from(mounted.container.querySelectorAll('button')).find((entry) => entry.textContent?.includes('Mark read'));
    button?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await flushPromises();
    await nextTick();

    expect(mounted.container.textContent).toContain('Card changed in Deck');
    expect(mounted.container.textContent).toContain('2');
    expect(setNotificationReadState).toHaveBeenCalledWith('notification-1', true);
    mounted.unmount();
  });

  test('marks all notifications read and reloads unread list', async () => {
    fetchNotifications.mockResolvedValue(pagePayload([notification()]));
    markAllNotificationsRead.mockResolvedValue({ updated_count: 1, unread_count: 0 });

    const mounted = await mountView();
    const markAllButton = Array.from(mounted.container.querySelectorAll('button')).find((entry) => entry.textContent?.includes('Mark all read'));
    markAllButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await flushPromises();
    await nextTick();

    expect(markAllNotificationsRead).toHaveBeenCalled();
    expect(unreadNotificationCount.value).toBe(0);
    expect(fetchNotifications).toHaveBeenCalledTimes(2);
    mounted.unmount();
  });
});
