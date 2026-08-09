import { describe, expect, test, vi } from 'vitest';
import { api } from '@/shared/api/client';
import { fetchOperationsQueuePage } from '@/domain/operations/api';

vi.mock('@/shared/api/client', () => ({
  api: { get: vi.fn() },
  toAbsoluteApiUrl: vi.fn((value: string) => value),
}));

describe('operations domain api', () => {
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
