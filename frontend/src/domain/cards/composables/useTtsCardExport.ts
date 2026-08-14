import { readonly, ref, type DeepReadonly, type Ref } from 'vue';
import { toast } from 'vue-sonner';
import { exportTtsCards, type TtsCardExportSource } from '@/domain/cards/api';
import { ttsExportSheetDescription } from '@/domain/cards/utils/ttsExportResponse';
import { getApiErrorMessage } from '@/shared/api/errors';

export type UseTtsCardExportResult = {
  isExportingTtsCards: DeepReadonly<Ref<boolean>>;
  copyTtsCardExport: (
    source: TtsCardExportSource,
    isRequestCurrent?: () => boolean,
  ) => Promise<void>;
  invalidateTtsCardExport: () => void;
};

export const useTtsCardExport = (): UseTtsCardExportResult => {
  const isExportingTtsCards = ref(false);
  let exportGeneration = 0;

  const invalidateTtsCardExport = (): void => {
    exportGeneration += 1;
  };

  const copyTtsCardExport = async (
    source: TtsCardExportSource,
    isRequestCurrent: () => boolean = () => true,
  ): Promise<void> => {
    if (isExportingTtsCards.value) return;
    const generation = exportGeneration;
    const requestIsCurrent = (): boolean =>
      generation === exportGeneration && isRequestCurrent();
    isExportingTtsCards.value = true;
    try {
      const result = await exportTtsCards(source);
      if (!requestIsCurrent()) {
        return;
      }
      await navigator.clipboard.writeText(result.encodedPayload);
      if (!requestIsCurrent()) {
        return;
      }
      const cardLabel = `${result.exportedCount} TTS card${result.exportedCount === 1 ? '' : 's'} copied to clipboard`;
      toast.success(cardLabel, { description: ttsExportSheetDescription(result) });
    } catch (error) {
      if (!requestIsCurrent()) {
        return;
      }
      console.error('TTS card export failed', error);
      toast.error('TTS card export failed', {
        description: getApiErrorMessage(error, 'The export could not be created.'),
      });
    } finally {
      isExportingTtsCards.value = false;
    }
  };

  return {
    isExportingTtsCards: readonly(isExportingTtsCards),
    copyTtsCardExport,
    invalidateTtsCardExport,
  };
};
