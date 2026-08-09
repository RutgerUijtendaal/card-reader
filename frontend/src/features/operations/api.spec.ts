import { describe, expect, test, vi } from 'vitest';
import { api } from '@/shared/api/client';
import { fetchOperationsOverview, fetchOperationsQueuePage } from '@/features/operations/api';

vi.mock('@/shared/api/client', () => ({
  api: { get: vi.fn() },
  toAbsoluteApiUrl: vi.fn((value: string) => value),
}));

describe('operations api', () => {
  test('fetches the staff operations overview', async () => {
    const overview = { generated_at: '2026-08-08T10:00:00Z', workers: [], queues: [] };
    vi.mocked(api.get).mockResolvedValueOnce({ data: overview });

    await expect(fetchOperationsOverview()).resolves.toEqual(overview);
    expect(api.get).toHaveBeenCalledWith('/operations?include_items=false');
  });

  test('fetches a paged queue history', async () => {
    const page = {
      count: 0,
      next_page: null,
      previous_page: 1,
      page: 2,
      page_size: 20,
      results: [],
    };
    vi.mocked(api.get).mockResolvedValueOnce({ data: page });

    await expect(fetchOperationsQueuePage('developer-data-builds', 2, 20)).resolves.toEqual(page);
    expect(api.get).toHaveBeenCalledWith(
      '/operations/queues/developer-data-builds?page=2&page_size=20',
    );
  });
});
