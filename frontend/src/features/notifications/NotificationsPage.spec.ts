import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import NotificationsPage from '@/features/notifications/NotificationsPage.vue';
import type { NotificationPage, UserNotification } from '@/domain/notifications/types';

const { fetchNotifications, markAllNotificationsRead, setNotificationReadState, unreadNotificationCount } = vi.hoisted(() => ({
  fetchNotifications: vi.fn(),
  markAllNotificationsRead: vi.fn(),
  setNotificationReadState: vi.fn(),
  unreadNotificationCount: { value: 1, __v_isRef: true },
}));

vi.mock('@/domain/notifications/api', () => ({
  buildNotificationSearchParams: (page: number, pageSize: number, eventType?: string | null) => {
    const params = new URLSearchParams();
    params.set('page', String(page));
    params.set('page_size', String(pageSize));
    if (eventType) {
      params.set('event_type', eventType);
    }
    return params;
  },
  fetchNotifications,
  markAllNotificationsRead,
  setNotificationReadState,
}));

vi.mock('@/domain/notifications/composables/useNotificationSummary', () => ({
  useNotificationSummary: () => ({
    unreadNotificationCount,
    loadNotificationSummary: vi.fn(),
    setUnreadNotificationCount: (count: number) => {
      unreadNotificationCount.value = count;
    },
  }),
}));

vi.mock('@/features/notifications/components/NotificationCardVersionComparison.vue', () => ({
  default: {
    template: '<div data-testid="version-comparison">Version comparison</div>',
  },
}));

const notification = (overrides: Partial<UserNotification> = {}): UserNotification => ({
  id: 'notification-1',
  event_type: 'deck.card_version_changed',
  subject_type: 'deck_card',
  subject_id: 'deck-1:card-1',
  target_url: '/my/decks/deck-1',
  title: 'Card changed in Deck',
  message: 'A card changed.',
  metadata: {
    deck_id: 'deck-1',
    deck_name: 'Deck',
    card_id: 'card-1',
    card_name: 'Changed Card',
    card_version_id: 'version-2',
    previous_card_version_id: 'version-1',
    change_cause: 'import_created',
  },
  event_count: 2,
  read_at: null,
  created_at: '2026-06-07T10:00:00Z',
  updated_at: '2026-06-07T10:00:00Z',
  last_event_at: '2026-06-07T10:00:00Z',
  actor: null,
  ...overrides,
});

const pagePayload = (
  results: UserNotification[],
  overrides: Partial<NotificationPage> = {},
): NotificationPage => ({
  count: results.length,
  next_page: null,
  previous_page: null,
  page: 1,
  page_size: 25,
  results,
  ...overrides,
});

const flushPromises = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
};

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, reject, resolve };
};

const mountView = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/notifications', component: NotificationsPage },
      { path: '/my/decks/:id', component: { template: '<div />' } },
      { path: '/cards/:id', component: { template: '<div />' } },
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
    localStorage.clear();
    document.body.innerHTML = '';
  });

  test('marks a clicked row read and toggles its details while keeping it visible', async () => {
    const row = notification();
    fetchNotifications.mockResolvedValue(pagePayload([row]));
    setNotificationReadState.mockResolvedValue(notification({ read_at: '2026-06-07T10:01:00Z' }));

    const mounted = await mountView();
    const notificationRow = mounted.container.querySelector<HTMLElement>('[data-notification-id="notification-1"]');
    notificationRow?.click();
    await flushPromises();
    await nextTick();

    expect(mounted.container.textContent).toContain('Changed Card changed in Deck');
    expect(mounted.container.textContent).toContain('2 updates while unread');
    expect(mounted.container.textContent).toContain('Version comparison');
    expect(mounted.container.textContent).not.toContain('Mark read');
    expect(mounted.container.textContent).not.toContain('Mark unread');
    expect(setNotificationReadState).toHaveBeenCalledWith('notification-1', true);
    expect(fetchNotifications).toHaveBeenCalledTimes(1);
    expect(mounted.container.querySelector('[data-notification-id="notification-1"]')).not.toBeNull();
    expect(notificationRow?.getAttribute('role')).toBeNull();
    const detailsTrigger = notificationRow?.querySelector<HTMLButtonElement>('[data-testid="notification-details-trigger"]');
    expect(detailsTrigger?.getAttribute('aria-expanded')).toBe('true');
    const actions = mounted.container.querySelector('[data-testid="notification-actions"]');
    expect(actions?.querySelectorAll('a')).toHaveLength(2);
    expect(actions?.textContent?.trim()).toBe('');
    expect(actions?.querySelector('[aria-label="View deck"]')).not.toBeNull();
    expect(actions?.querySelector('[aria-label="View card"]')).not.toBeNull();
    const notificationDetails = mounted.container.querySelector('[data-testid="notification-details"]');
    expect(notificationDetails?.parentElement).toBe(notificationRow);
    expect(notificationDetails?.classList.contains('ml-12')).toBe(true);

    detailsTrigger?.click();
    await nextTick();

    expect(detailsTrigger?.getAttribute('aria-expanded')).toBe('false');
    expect(mounted.container.textContent).not.toContain('Version comparison');
    expect(setNotificationReadState).toHaveBeenCalledTimes(1);
    mounted.unmount();
  });

  test('optimistically marks a notification read when an action opens', async () => {
    fetchNotifications.mockResolvedValue(pagePayload([notification()]));
    setNotificationReadState.mockResolvedValue(notification({ read_at: '2026-06-07T10:01:00Z' }));

    const mounted = await mountView();
    const cardLink = mounted.container.querySelector<HTMLAnchorElement>('a[aria-label="View card"]');
    const cardTooltipTrigger = cardLink?.parentElement;
    expect(cardLink?.hasAttribute('title')).toBe(false);
    cardTooltipTrigger?.dispatchEvent(new MouseEvent('mouseenter'));
    await nextTick();
    expect(document.body.querySelector('[role="tooltip"]')?.textContent).toBe('View card');
    expect(cardLink?.getAttribute('aria-describedby')).toBe(document.body.querySelector('[role="tooltip"]')?.id);
    cardLink?.addEventListener('click', (event) => event.preventDefault(), { once: true });
    cardLink?.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, ctrlKey: true }));
    await nextTick();

    expect(setNotificationReadState).toHaveBeenCalledWith('notification-1', true);
    expect(unreadNotificationCount.value).toBe(0);
    await flushPromises();
    await nextTick();
    expect(fetchNotifications).toHaveBeenCalledTimes(1);
    expect(mounted.container.textContent).toContain('Changed Card changed in Deck');
    expect(mounted.container.textContent).not.toContain('Mark unread');
    mounted.unmount();
  });

  test('renders flag review status and marks it read when expanding multiline details', async () => {
    const flagRow = notification({
      event_type: 'parse_flag_item.reviewed',
      event_count: 1,
      actor: { id: 'reviewer-1', username: 'reviewer' },
      metadata: {
        card_id: 'card-1',
        card_name: 'Flagged Card',
        card_version_id: 'version-2',
        property_key: 'rules_text',
        property_label: 'rules text flag',
        status: 'resolved',
        submitted_value: 'Correct rules',
        submission_note: 'First line\nSecond line',
        review_note: 'Fixed from the source image.',
      },
    });
    fetchNotifications.mockResolvedValue(pagePayload([flagRow]));
    setNotificationReadState.mockResolvedValue({
      ...flagRow,
      read_at: '2026-06-07T10:01:00Z',
    });

    const mounted = await mountView();
    const notificationRow = mounted.container.querySelector<HTMLElement>('[data-notification-id="notification-1"]');
    notificationRow?.click();
    await flushPromises();
    await nextTick();

    expect(mounted.container.textContent).toContain('Flag review');
    expect(mounted.container.textContent).toContain('resolved');
    expect(mounted.container.textContent).toContain('Your suggestion');
    expect(mounted.container.textContent).toContain('First line\nSecond line');
    const viewCardLink = mounted.container.querySelector<HTMLAnchorElement>('a[aria-label="View card"]');
    expect(viewCardLink?.getAttribute('href')).toContain('/cards/card-1?');
    expect(viewCardLink?.getAttribute('href')).toContain('version_id=version-2');
    expect(viewCardLink?.getAttribute('href')).toContain('return_to=notifications');
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
    expect(fetchNotifications).toHaveBeenCalledTimes(1);
    expect(mounted.container.querySelector('.notification-row-read')).not.toBeNull();
    mounted.unmount();
  });

  test('does not roll back a successful mark-all update when a pending row update fails', async () => {
    unreadNotificationCount.value = 2;
    const rowUpdate = deferred<UserNotification>();
    fetchNotifications.mockResolvedValue(pagePayload([notification()]));
    setNotificationReadState.mockReturnValue(rowUpdate.promise);
    markAllNotificationsRead.mockResolvedValue({ updated_count: 2, unread_count: 0 });

    const mounted = await mountView();
    const notificationRow = mounted.container.querySelector<HTMLElement>('[data-notification-id="notification-1"]');
    notificationRow?.click();
    await nextTick();

    const markAllButton = Array.from(mounted.container.querySelectorAll('button')).find((entry) =>
      entry.textContent?.includes('Mark all read'),
    );
    markAllButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await flushPromises();
    await nextTick();

    rowUpdate.reject(new Error('Row update failed'));
    await flushPromises();
    await nextTick();

    expect(unreadNotificationCount.value).toBe(0);
    expect(notificationRow?.classList.contains('notification-row-read')).toBe(true);
    mounted.unmount();
  });

  test('shows type-specific empty states and sends the selected event filter', async () => {
    fetchNotifications.mockResolvedValue(pagePayload([]));

    const mounted = await mountView();

    expect(mounted.container.textContent).toContain('No notifications yet');

    const flagButton = Array.from(mounted.container.querySelectorAll('button')).find((entry) =>
      entry.textContent?.includes('Flag reviews'),
    );
    flagButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await flushPromises();
    await nextTick();

    expect(mounted.container.textContent).toContain('No flag review notifications');
    const lastParams = fetchNotifications.mock.calls.at(-1)?.[0] as URLSearchParams;
    expect(lastParams.get('event_type')).toBe('parse_flag_item.reviewed');
    mounted.unmount();
  });

  test('ignores an earlier response after the notification filter changes', async () => {
    const initialRequest = deferred<NotificationPage>();
    fetchNotifications
      .mockReturnValueOnce(initialRequest.promise)
      .mockResolvedValueOnce(pagePayload([]));

    const mounted = await mountView();
    const flagButton = Array.from(mounted.container.querySelectorAll('button')).find((entry) =>
      entry.textContent?.includes('Flag reviews'),
    );
    flagButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await flushPromises();
    await nextTick();

    expect(mounted.container.textContent).toContain('No flag review notifications');

    initialRequest.resolve(pagePayload([notification()]));
    await flushPromises();
    await nextTick();

    expect(mounted.container.textContent).toContain('No flag review notifications');
    expect(mounted.container.querySelector('[data-notification-id]')).toBeNull();
    mounted.unmount();
  });

  test('offers the shared card-size slider in view options', async () => {
    localStorage.setItem('card-reader.gallery-options', JSON.stringify({ cardScale: 1.2 }));
    fetchNotifications.mockResolvedValue(pagePayload([]));

    const mounted = await mountView();
    const viewOptionsButton = Array.from(mounted.container.querySelectorAll('button')).find((entry) =>
      entry.textContent?.includes('View Options'),
    );
    viewOptionsButton?.click();
    await nextTick();

    const cardSizeSlider = document.body.querySelector<HTMLInputElement>('input[type="range"]');
    expect(document.body.textContent).toContain('Card Size');
    expect(cardSizeSlider?.value).toBe('1.2');

    mounted.unmount();
  });

  test('appends the next notification page with the existing load-more pattern', async () => {
    fetchNotifications
      .mockResolvedValueOnce(pagePayload([notification()], { count: 2, next_page: 2 }))
      .mockResolvedValueOnce(pagePayload([
        notification({ id: 'notification-2', subject_id: 'deck-2:card-2' }),
      ], { count: 2, page: 2, previous_page: 1 }));

    const mounted = await mountView();
    const loadMoreButton = Array.from(mounted.container.querySelectorAll('button')).find((entry) =>
      entry.textContent?.includes('Load more'),
    );
    loadMoreButton?.click();
    await flushPromises();
    await nextTick();

    expect(fetchNotifications).toHaveBeenCalledTimes(2);
    const secondParams = fetchNotifications.mock.calls[1]?.[0] as URLSearchParams;
    expect(secondParams.get('page')).toBe('2');
    expect(mounted.container.querySelectorAll('[data-notification-id]')).toHaveLength(2);
    mounted.unmount();
  });
});
