import { describe, expect, test } from 'vitest';
import {
  defaultOperationsQueueKey,
  operationsProgressPercent,
  parseOperationsPage,
  workerStatusLabel,
} from '@/features/operations/utils/operationsUtils';
import type {
  OperationsQueue,
  OperationsQueueItem,
  WorkerOverview,
} from '@/features/operations/types';

describe('operations utils', () => {
  test('labels online worker activity', () => {
    const worker: WorkerOverview = {
      key: 'parser',
      display_name: 'Parser worker',
      queue_key: 'imports',
      health: 'online',
      activity: 'busy',
      active_instances: 1,
      last_seen_at: '2026-08-08T10:00:00Z',
      current_work_ids: ['job-1'],
      instances: [],
    };

    expect(workerStatusLabel(worker)).toBe('Online · Busy');
  });

  test('handles bounded and unavailable progress', () => {
    const item = {
      progress_current: 4,
      progress_total: 10,
    } as OperationsQueueItem;
    expect(operationsProgressPercent(item)).toBe(40);
    expect(operationsProgressPercent({ ...item, progress_total: 0 })).toBeNull();
  });

  test('prioritizes queues needing attention, then non-empty queues', () => {
    const queue = (key: string, total: number, failed = 0): OperationsQueue => ({
      key,
      display_name: key,
      worker_key: `${key}-worker`,
      total_count: total,
      status_counts: {
        scheduled: 0,
        queued: 0,
        running: 0,
        canceling: 0,
        retrying: 0,
        completed: total - failed,
        failed,
        cancelled: 0,
      },
      items: [],
    });

    expect(defaultOperationsQueueKey([queue('empty', 0), queue('history', 3)])).toBe('history');
    expect(defaultOperationsQueueKey([queue('history', 3), queue('attention', 1, 1)])).toBe(
      'attention',
    );
    expect(defaultOperationsQueueKey([])).toBeNull();
  });

  test('normalizes route page values', () => {
    expect(parseOperationsPage('3')).toBe(3);
    expect(parseOperationsPage(['2', '4'])).toBe(2);
    expect(parseOperationsPage('invalid')).toBe(1);
    expect(parseOperationsPage('0')).toBe(1);
  });
});
