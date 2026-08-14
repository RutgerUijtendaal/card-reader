import { beforeEach, describe, expect, test, vi } from 'vitest';
import {
  exportTtsCards,
  fetchCardFilters,
  fetchCardPage,
  fetchCards,
  type TtsCardExportSource,
} from '@/domain/cards/api';
import { api } from '@/shared/api/client';

vi.mock('@/shared/api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('card API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('maps the structured TTS export response', async () => {
    const source: TtsCardExportSource = {
      type: 'content_version',
      content_version_id: 'version-1',
    };
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        encoded_payload: 'encoded-export',
        exported_count: 3,
        skipped_count: 1,
        sheet_count: 2,
      },
    });

    await expect(exportTtsCards(source)).resolves.toEqual({
      encodedPayload: 'encoded-export',
      exportedCount: 3,
      skippedCount: 1,
      sheetCount: 2,
    });
    expect(api.post).toHaveBeenCalledWith('/exports/tts/cards', { source });
  });

  test('loads paginated card contracts from default and focused endpoints', async () => {
    const page = {
      count: 0,
      next_page: null,
      previous_page: null,
      page: 1,
      page_size: 25,
      results: [],
    };
    vi.mocked(api.get).mockResolvedValue({ data: page });

    await expect(
      fetchCardPage('/review/confidence-cards', new URLSearchParams({ page: '1' })),
    ).resolves.toEqual(page);
    await expect(fetchCards({ q: 'hero', page_size: 25 })).resolves.toEqual(page);

    expect(api.get).toHaveBeenNthCalledWith(1, '/review/confidence-cards?page=1');
    expect(api.get).toHaveBeenNthCalledWith(2, '/cards', {
      params: { q: 'hero', page_size: 25 },
    });
  });

  test('loads global or exact-pool filter metadata explicitly', async () => {
    const response = { keywords: [], tags: [], symbols: [], types: [] };
    vi.mocked(api.get).mockResolvedValue({ data: response });

    await expect(fetchCardFilters()).resolves.toEqual(response);
    await expect(fetchCardFilters('evil')).resolves.toEqual(response);

    expect(api.get).toHaveBeenNthCalledWith(1, '/cards/filters');
    expect(api.get).toHaveBeenNthCalledWith(2, '/cards/filters', {
      params: { card_pool: 'evil' },
    });
  });
});
