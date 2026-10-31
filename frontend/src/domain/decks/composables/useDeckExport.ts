import { toast } from 'vue-sonner';
import { exportDeckTts } from '@/domain/decks/api';
import { getApiErrorMessage } from '@/shared/api/errors';
import { copyTtsExport } from '@/domain/cards/utils/copyTtsExport';

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
      await copyTtsExport(result, options.successMessage ?? 'TTS deck copied to clipboard');
    } catch (error) {
      console.error('TTS deck export failed', error);
      toast.error('TTS deck export failed', {
        description: getApiErrorMessage(error, 'The export could not be created.'),
      });
    }
  };

  return { exportTtsDeck };
};
