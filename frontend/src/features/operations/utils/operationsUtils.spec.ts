import { describe, expect, test } from 'vitest';
import {
  operationsProgressPercent,
  workerStatusLabel,
} from '@/features/operations/utils/operationsUtils';
import type { OperationsQueueItem, WorkerOverview } from '@/features/operations/types';

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
});
