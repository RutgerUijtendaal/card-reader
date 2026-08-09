/* eslint-disable vue/one-component-per-file */
import { createApp, nextTick } from 'vue';
import { afterEach, describe, expect, test } from 'vitest';
import OperationsQueueItemRow from '@/features/operations/components/OperationsQueueItemRow.vue';
import type { OperationsQueueItem } from '@/features/operations/types';

const item: OperationsQueueItem = {
  id: 'build-1',
  title: 'dev-2026-08-09',
  status: 'failed',
  native_status: 'failed',
  created_at: '2026-08-09T10:00:00Z',
  updated_at: '2026-08-09T10:02:00Z',
  started_at: '2026-08-09T10:01:00Z',
  finished_at: null,
  progress_current: null,
  progress_total: null,
  error_message: 'The build failed with a detailed explanation.',
  metadata: [{ label: 'Requested by', value: 'foo' }],
  links: [],
};

describe('OperationsQueueItemRow', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('keeps variable metadata collapsed until the row is expanded', async () => {
    const host = document.createElement('div');
    document.body.appendChild(host);
    const app = createApp(OperationsQueueItemRow, { item, expanded: false });
    app.mount(host);

    expect(host.textContent).toContain(item.title);
    expect(host.textContent).not.toContain(item.error_message);
    expect(host.textContent).not.toContain('Requested by');
    expect(host.querySelector('button')?.getAttribute('aria-expanded')).toBe('false');

    app.unmount();
    const expandedApp = createApp(OperationsQueueItemRow, { item, expanded: true });
    expandedApp.mount(host);
    await nextTick();

    expect(host.textContent).toContain(item.error_message);
    expect(host.textContent).toContain('Requested by');
    expect(host.querySelector('button')?.getAttribute('aria-expanded')).toBe('true');

    expandedApp.unmount();
  });
});
