import { toast } from 'vue-sonner';
import { exportDeckTts } from '@/modules/decks/api';

export type UseDeckExportResult = {
  exportTtsDeck: (deckId: string, options?: ExportTtsDeckOptions) => Promise<void>;
};

export type ExportTtsDeckOptions = {
  sideboardId?: string;
  successMessage?: string;
};

export const useDeckExport = (): UseDeckExportResult => {
  const exportTtsDeck = async (deckId: string, options: ExportTtsDeckOptions = {}): Promise<void> => {
    try {
      const blob = await exportDeckTts(deckId, options.sideboardId);
      await navigator.clipboard.writeText(await blob.text());

      toast.success(options.successMessage ?? 'TTS deck copied to clipboard');
    } catch (error) {
      console.error('TTS deck export failed', error);
      toast.error('TTS deck export failed', {
        description: 'Check the browser console for details.',
      });
    }
  };

  return { exportTtsDeck };
};
