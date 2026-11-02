import { toast } from 'vue-sonner';
import { showTtsExportFallback } from '@/domain/cards/composables/useTtsExportFallback';
import { ttsExportSheetDescription, type TtsExportResponse } from './ttsExportResponse';

export type CopyTtsExportOptions = {
  /** Overrides the default "N cards copied" plus sheet summary under the toast title. */
  description?: string;
  /** Checked after the clipboard write settles; a stale export shows nothing. */
  isCurrent?: () => boolean;
};

/**
 * Copies a TTS export to the clipboard and confirms it. When the browser refuses the clipboard
 * write, the shared fallback dialog shows the import code for manual copying instead of failing.
 */
export const copyTtsExport = async (
  result: TtsExportResponse,
  message: string,
  options: CopyTtsExportOptions = {},
): Promise<void> => {
  const isCurrent = options.isCurrent ?? (() => true);
  let copied = true;
  try {
    await navigator.clipboard.writeText(result.encodedPayload);
  } catch {
    copied = false;
  }
  if (!isCurrent()) {
    return;
  }
  if (!copied) {
    showTtsExportFallback(result);
    return;
  }
  toast.success(message, {
    description:
      options.description ??
      [
        `${result.exportedCount} card${result.exportedCount === 1 ? '' : 's'} copied.`,
        ttsExportSheetDescription(result),
      ].join(' '),
  });
};
