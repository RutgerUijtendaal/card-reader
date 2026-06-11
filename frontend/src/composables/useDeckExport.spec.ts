import { beforeEach, describe, expect, test, vi } from 'vitest';
import { useDeckExport } from '@/composables/useDeckExport';
import { exportDeckTts } from '@/modules/decks/api';
import { toast } from 'vue-sonner';

vi.mock('@/modules/decks/api', () => ({
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
    vi.mocked(exportDeckTts).mockResolvedValue(new Blob(['tts import script']));

    const { exportTtsDeck } = useDeckExport();
    await exportTtsDeck('deck-1');

    expect(exportDeckTts).toHaveBeenCalledWith('deck-1', undefined);
    expect(clipboardWriteText).toHaveBeenCalledWith('tts import script');
    expect(toast.success).toHaveBeenCalledWith('TTS deck copied to clipboard');
  });

  test('copies sideboard exports with custom success copy', async () => {
    vi.mocked(exportDeckTts).mockResolvedValue(new Blob(['sideboard script']));

    const { exportTtsDeck } = useDeckExport();
    await exportTtsDeck('deck-1', {
      sideboardId: 'side-1',
      successMessage: 'TTS sideboard copied to clipboard',
    });

    expect(exportDeckTts).toHaveBeenCalledWith('deck-1', 'side-1');
    expect(clipboardWriteText).toHaveBeenCalledWith('sideboard script');
    expect(toast.success).toHaveBeenCalledWith('TTS sideboard copied to clipboard');
  });
});
