import { beforeEach, describe, expect, test, vi } from 'vitest';
import { toast } from 'vue-sonner';
import { exportTtsCards } from '@/domain/cards/api';
import { useTtsCardExport } from '@/domain/cards/composables/useTtsCardExport';

vi.mock('@/domain/cards/api', () => ({
  exportTtsCards: vi.fn(),
}));

vi.mock('vue-sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

describe('useTtsCardExport', () => {
  const clipboardWriteText = vi.fn<(text: string) => Promise<void>>();

  beforeEach(() => {
    vi.clearAllMocks();
    clipboardWriteText.mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: clipboardWriteText },
    });
  });

  test('passes the gallery source unchanged and copies its base64 payload', async () => {
    vi.mocked(exportTtsCards).mockResolvedValue({
      encodedPayload: 'base64-gallery',
      exportedCount: 3,
      skippedCount: 0,
      sheetCount: 1,
    });
    const source = {
      type: 'gallery' as const,
      filters: { q: 'dragon', keyword_ids: ['keyword-1'], sort: 'name_asc' as const },
    };

    const { copyTtsCardExport } = useTtsCardExport();
    await copyTtsCardExport(source);

    expect(exportTtsCards).toHaveBeenCalledWith(source);
    expect(clipboardWriteText).toHaveBeenCalledWith('base64-gallery');
    expect(toast.success).toHaveBeenCalledWith('3 TTS cards copied to clipboard', {
      description: 'Uses 1 persistent sheet.',
    });
  });

  test('reports skipped cards for a content-version export', async () => {
    vi.mocked(exportTtsCards).mockResolvedValue({
      encodedPayload: 'base64-version',
      exportedCount: 2,
      skippedCount: 1,
      sheetCount: 2,
    });

    const { copyTtsCardExport } = useTtsCardExport();
    await copyTtsCardExport({ type: 'content_version', content_version_id: 'version-1' });

    expect(clipboardWriteText).toHaveBeenCalledWith('base64-version');
    expect(toast.success).toHaveBeenCalledWith('2 TTS cards copied to clipboard', {
      description: 'Uses 2 persistent sheets. 1 card could not be exported.',
    });
  });

  test('surfaces an API detail when the export fails', async () => {
    vi.mocked(exportTtsCards).mockRejectedValue({
      response: { data: { detail: 'Current card back is missing.' } },
    });

    const { copyTtsCardExport } = useTtsCardExport();
    await copyTtsCardExport({ type: 'content_version', content_version_id: 'version-1' });

    expect(clipboardWriteText).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith('TTS card export failed', {
      description: 'Current card back is missing.',
    });
  });
});
