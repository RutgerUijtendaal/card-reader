import { toast } from 'vue-sonner';
import { ttsExportSheetDescription, type TtsExportResponse } from './ttsExportResponse';

export const copyTtsExport = async (result: TtsExportResponse, message: string): Promise<void> => {
  await navigator.clipboard.writeText(result.encodedPayload);
  toast.success(message, {
    description: [
      `${result.exportedCount} card${result.exportedCount === 1 ? '' : 's'} copied.`,
      ttsExportSheetDescription(result),
    ].join(' '),
  });
};
