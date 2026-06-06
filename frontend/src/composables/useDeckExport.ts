import { toast } from 'vue-sonner';
import { exportDeckTts } from '@/modules/decks/api';

export type UseDeckExportResult = {
  exportTtsDeck: (deckId: string, deckName: string) => Promise<void>;
};

export const useDeckExport = (): UseDeckExportResult => {
  const exportTtsDeck = async (deckId: string, deckName: string): Promise<void> => {
    try {
      const blob = await exportDeckTts(deckId);
      const url = URL.createObjectURL(blob);

      try {
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `${slugifyDeckName(deckName)}.tts.txt`;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
      } finally {
        URL.revokeObjectURL(url);
      }

      toast.success('TTS deck exported');
    } catch (error) {
      console.error('TTS deck export failed', error);
      toast.error('TTS deck export failed', {
        description: 'Check the browser console for details.',
      });
    }
  };

  return { exportTtsDeck };
};

const slugifyDeckName = (value: string): string => {
  const normalized = value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return normalized || 'deck';
};
