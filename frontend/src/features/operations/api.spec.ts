import { describe, expect, test, vi } from 'vitest';
import { api } from '@/shared/api/client';
import { fetchOperationsOverview } from '@/features/operations/api';

vi.mock('@/shared/api/client', () => ({
  api: { get: vi.fn() },
  toAbsoluteApiUrl: vi.fn((value: string) => value),
}));

describe('operations api', () => {
  test('fetches the staff operations overview', async () => {
    const overview = { generated_at: '2026-08-08T10:00:00Z', workers: [], queues: [] };
    vi.mocked(api.get).mockResolvedValueOnce({ data: overview });

    await expect(fetchOperationsOverview()).resolves.toEqual(overview);
    expect(api.get).toHaveBeenCalledWith('/operations');
  });
});
