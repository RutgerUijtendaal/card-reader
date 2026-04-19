import { isTauri } from '@tauri-apps/api/core';
import { save } from '@tauri-apps/plugin-dialog';
import { writeFile } from '@tauri-apps/plugin-fs';
import { toast } from 'vue-sonner';
import { api } from '@/api/client';

export type UseCsvExportResult = {
  exportCardsCsv: (params: URLSearchParams) => Promise<void>;
};

export const useCsvExport = (): UseCsvExportResult => {
  const exportCardsCsv = async (params: URLSearchParams): Promise<void> => {
    try {
      const query = params.toString();
      const path = query ? `/exports/csv?${query}` : '/exports/csv';
      const response = await api.get<Blob>(path, { responseType: 'blob' });

      if (isTauri()) {
        const targetPath = await save({
          defaultPath: 'cards.csv',
          filters: [
            {
              name: 'CSV',
              extensions: ['csv'],
            },
          ],
        });

        if (!targetPath) {
          return;
        }

        await writeFile(targetPath, new Uint8Array(await response.data.arrayBuffer()));
        toast.success('CSV exported');
        return;
      }

      const url = URL.createObjectURL(response.data);
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
      toast.success('CSV exported');
    } catch (error) {
      console.error('CSV export failed', error);
      toast.error('CSV export failed', {
        description: 'Check desktop log and devtools console for details.',
      });
    }
  };

  return { exportCardsCsv };
};
