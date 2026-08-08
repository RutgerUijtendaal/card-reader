import { beforeEach, describe, expect, test, vi } from 'vitest';
import { useDeckExport } from '@/domain/decks/composables/useDeckExport';
import { exportDeckTts } from '@/domain/decks/api';
import { toast } from 'vue-sonner';

vi.mock('@/domain/decks/api', () => ({
  exportDeckTts: vi.fn(),
}));

vi.mock('vue-sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

describe('useDeckExport', () => {
  const clipboardWriteText = vi.fn<(text: string) => Promise<void>>();

  beforeEach(() => {
    vi.clearAllMocks();
    clipboardWriteText.mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: clipboardWriteText,
      },
    });
  });

  test('copies the TTS export text to the clipboard', async () => {
    vi.mocked(exportDeckTts).mockResolvedValue({
      encodedPayload: 'tts import script',
      exportedCount: 61,
      skippedCount: 0,
      sheetCount: 2,
    });

    const { exportTtsDeck } = useDeckExport();
    await exportTtsDeck('deck-1');

    expect(exportDeckTts).toHaveBeenCalledWith('deck-1', undefined);
    expect(clipboardWriteText).toHaveBeenCalledWith('tts import script');
    expect(toast.success).toHaveBeenCalledWith('TTS deck copied to clipboard', {
      description: '61 cards copied. Uses 2 persistent sheets.',
    });
  });

  test('copies sideboard exports with custom success copy', async () => {
    vi.mocked(exportDeckTts).mockResolvedValue({
      encodedPayload: 'sideboard script',
      exportedCount: 6,
      skippedCount: 1,
      sheetCount: 1,
    });

    const { exportTtsDeck } = useDeckExport();
    await exportTtsDeck('deck-1', {
      sideboardId: 'side-1',
      successMessage: 'TTS sideboard copied to clipboard',
    });

    expect(exportDeckTts).toHaveBeenCalledWith('deck-1', 'side-1');
    expect(clipboardWriteText).toHaveBeenCalledWith('sideboard script');
    expect(toast.success).toHaveBeenCalledWith('TTS sideboard copied to clipboard', {
      description: '6 cards copied. Uses 1 persistent sheet. 1 card could not be exported.',
    });
  });

  test('surfaces an API detail when deck export fails', async () => {
    vi.mocked(exportDeckTts).mockRejectedValue({
      response: { data: { detail: 'Required deck hero is unavailable.' } },
    });

    const { exportTtsDeck } = useDeckExport();
    await exportTtsDeck('deck-1');

    expect(clipboardWriteText).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith('TTS deck export failed', {
      description: 'Required deck hero is unavailable.',
    });
  });
});
