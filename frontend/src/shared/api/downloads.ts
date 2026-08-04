import { api } from '@/shared/api/client';

export const fetchBlob = async (path: string): Promise<Blob> => {
  const response = await api.get<Blob>(path, { responseType: 'blob' });
  return response.data;
};
