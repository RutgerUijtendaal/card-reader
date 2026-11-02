import { afterEach, describe, expect, test, vi } from 'vitest';
import { copyTtsExport } from '@/domain/cards/utils/copyTtsExport';
import { useTtsExportFallback } from '@/domain/cards/composables/useTtsExportFallback';
import type { TtsExportResponse } from '@/domain/cards/utils/ttsExportResponse';

const toastSuccess = vi.hoisted(() => vi.fn());
vi.mock('vue-sonner', () => ({ toast: { success: toastSuccess } }));

const result = {
  encodedPayload: 'tts-code',
  exportedCount: 2,
  sheets: [],
} as unknown as TtsExportResponse;

const stubClipboard = (writeText: () => Promise<void>): void => {
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
};

describe('copyTtsExport', () => {
  afterEach(() => {
    useTtsExportFallback().dismiss();
    vi.clearAllMocks();
  });

  test('copies the import code and confirms it', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    stubClipboard(writeText);

    await copyTtsExport(result, 'TTS deck copied to clipboard');

    expect(writeText).toHaveBeenCalledWith('tts-code');
    expect(toastSuccess).toHaveBeenCalledWith('TTS deck copied to clipboard', expect.anything());
    expect(useTtsExportFallback().fallback.value).toBeNull();
  });

  test('hands the import code to the shared fallback when the clipboard is unavailable', async () => {
    stubClipboard(vi.fn().mockRejectedValue(new Error('denied')));

    await expect(copyTtsExport(result, 'TTS deck copied to clipboard')).resolves.toBeUndefined();

    expect(toastSuccess).not.toHaveBeenCalled();
    expect(useTtsExportFallback().fallback.value?.payload).toBe('tts-code');
    expect(useTtsExportFallback().fallback.value?.summary).toContain('2 cards.');
  });
});
