import { beforeEach, describe, expect, test, vi } from 'vitest';
import { toast } from 'vue-sonner';
import { fetchBlob } from '@/shared/api/downloads';
import { useCsvExport } from '@/shared/composables/useCsvExport';

vi.mock('@/shared/api/downloads', () => ({
  fetchBlob: vi.fn(),
}));

vi.mock('vue-sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

describe('useCsvExport', () => {
  const createObjectUrl = vi.fn(() => 'blob:csv-export');

  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: createObjectUrl,
    });
  });

  test('drops browser side effects when the originating request is no longer current', async () => {
    vi.mocked(fetchBlob).mockResolvedValue(new Blob(['card data']));
    const { exportCardsCsv } = useCsvExport();
    await exportCardsCsv(new URLSearchParams('card_pool=evil'), () => false);

    expect(createObjectUrl).not.toHaveBeenCalled();
    expect(toast.success).not.toHaveBeenCalled();
    expect(toast.error).not.toHaveBeenCalled();
  });
});
