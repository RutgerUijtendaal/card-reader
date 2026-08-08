import { toast } from 'vue-sonner';
import { exportDeckTts } from '@/domain/decks/api';
import { getApiErrorMessage } from '@/shared/api/errors';
import { ttsExportSheetDescription } from '@/domain/cards/utils/ttsExportResponse';

export type UseDeckExportResult = {
  exportTtsDeck: (deckId: string, options?: ExportTtsDeckOptions) => Promise<void>;
};

export type ExportTtsDeckOptions = {
  sideboardId?: string;
  successMessage?: string;
};

export const useDeckExport = (): UseDeckExportResult => {
  const exportTtsDeck = async (
    deckId: string,
    options: ExportTtsDeckOptions = {},
  ): Promise<void> => {
    try {
      const result = await exportDeckTts(deckId, options.sideboardId);
      await navigator.clipboard.writeText(result.encodedPayload);

      toast.success(options.successMessage ?? 'TTS deck copied to clipboard', {
        description: [
          `${result.exportedCount} card${result.exportedCount === 1 ? '' : 's'} copied.`,
          ttsExportSheetDescription(result),
        ].join(' '),
      });
    } catch (error) {
      console.error('TTS deck export failed', error);
      toast.error('TTS deck export failed', {
        description: getApiErrorMessage(error, 'The export could not be created.'),
      });
    }
  };

  return { exportTtsDeck };
};
