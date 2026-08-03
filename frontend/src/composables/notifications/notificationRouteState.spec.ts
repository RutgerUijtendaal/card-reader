import { describe, expect, test } from 'vitest';
import {
  buildNotificationTargetLocation,
  buildNotificationsReturnLocation,
  isNotificationsReturnQuery,
} from '@/composables/notifications/notificationRouteState';

describe('notificationRouteState', () => {
  test('builds a notification return context around an existing target query', () => {
    const target = buildNotificationTargetLocation('/cards/card-1', { version_id: 'version-2' });

    expect(target).toEqual({
      path: '/cards/card-1',
      query: {
        version_id: 'version-2',
        return_to: 'notifications',
      },
    });
    expect(isNotificationsReturnQuery({ return_to: 'notifications' })).toBe(true);
    expect(buildNotificationsReturnLocation()).toEqual({ path: '/notifications' });
  });
});
