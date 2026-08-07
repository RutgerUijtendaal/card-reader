import { beforeEach, describe, expect, test, vi } from 'vitest';
import { exportTtsCards, type TtsCardExportSource } from '@/domain/cards/api';
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
});
