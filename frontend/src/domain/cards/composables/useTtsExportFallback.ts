import { readonly, ref } from 'vue';
import { ttsExportSheetDescription, type TtsExportResponse } from '@/domain/cards/utils/ttsExportResponse';

export type TtsExportFallback = {
  payload: string;
  summary: string;
};

// One app-wide fallback: any TTS export whose clipboard write fails hands its import code here,
// and the dialog mounted by the app shell shows it for manual copying.
const pendingFallback = ref<TtsExportFallback | null>(null);

export const showTtsExportFallback = (result: TtsExportResponse): void => {
  pendingFallback.value = {
    payload: result.encodedPayload,
    summary: [
      `${result.exportedCount} card${result.exportedCount === 1 ? '' : 's'}.`,
      ttsExportSheetDescription(result),
    ].join(' '),
  };
};

export const useTtsExportFallback = () => ({
  fallback: readonly(pendingFallback),
  dismiss: (): void => {
    pendingFallback.value = null;
  },
});
