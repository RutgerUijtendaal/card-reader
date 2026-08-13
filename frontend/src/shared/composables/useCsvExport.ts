import { toast } from 'vue-sonner';
import { fetchBlob } from '@/shared/api/downloads';

export type UseCsvExportResult = {
  exportCardsCsv: (
    params: URLSearchParams,
    isRequestCurrent?: () => boolean,
  ) => Promise<void>;
};

export const useCsvExport = (): UseCsvExportResult => {
  const exportCardsCsv = async (
    params: URLSearchParams,
    isRequestCurrent: () => boolean = () => true,
  ): Promise<void> => {
    try {
      const query = params.toString();
      const path = query ? `/exports/csv?${query}` : '/exports/csv';
      const blob = await fetchBlob(path);
      if (!isRequestCurrent()) {
        return;
      }

      const url = URL.createObjectURL(blob);
      try {
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = 'cards.csv';
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
      } finally {
        URL.revokeObjectURL(url);
      }
      if (!isRequestCurrent()) {
        return;
      }
      toast.success('CSV exported');
    } catch (error) {
      if (!isRequestCurrent()) {
        return;
      }
      console.error('CSV export failed', error);
      toast.error('CSV export failed', {
        description: 'Check the browser console for details.',
      });
    }
  };

  return { exportCardsCsv };
};
