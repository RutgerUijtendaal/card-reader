import { describe, expect, test, vi } from 'vitest';
import { api } from '@/shared/api/client';
import { createImportJob, fetchCurrentContentVersion, fetchImportJobs } from '@/features/import-jobs/api';

vi.mock('@/shared/api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('importJobs api', () => {
  test('fetches only active imports for the management page', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: [] });

    await expect(fetchImportJobs()).resolves.toEqual([]);
    expect(api.get).toHaveBeenCalledWith('/imports', { params: { status: 'active' } });
  });

  test('fetches the current content version', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        id: 'version-1',
        version_number: '14.1.2',
        base_version: '14.1',
        description: 'Current release.',
      },
    });

    await expect(fetchCurrentContentVersion()).resolves.toEqual({
      id: 'version-1',
      version_number: '14.1.2',
      base_version: '14.1',
      description: 'Current release.',
    });
    expect(api.get).toHaveBeenCalledWith('/imports/current-version');
  });

  test('sends version fields when creating an import job', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: {} });
    const file = new File(['image'], 'card.png', { type: 'image/png' });

    await createImportJob({
      templateId: 'mtg-like-v1',
      contentVersionBase: '14.1',
      contentVersionDescription: 'Current release.',
      files: [file],
    });

    const formData = vi.mocked(api.post).mock.calls[0]?.[1] as FormData;
    expect(api.post).toHaveBeenCalledWith(
      '/imports/upload',
      expect.any(FormData),
      expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } }),
    );
    expect(formData.get('template_id')).toBe('mtg-like-v1');
    expect(formData.get('content_version_base')).toBe('14.1');
    expect(formData.get('content_version_description')).toBe('Current release.');
    expect(formData.get('options_json')).toBe('{}');
    expect(formData.getAll('files')).toEqual([file]);
  });
});
