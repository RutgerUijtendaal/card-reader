import { ref } from 'vue';
import { toast } from 'vue-sonner';
import { uploadSymbolAsset } from '@/modules/settings/api/catalog';
import type { CatalogFormEntry, SymbolRecord } from '@/modules/settings/types';
import { appendAssetPath, extractErrorMessage, pickFile } from './catalogSettingsUtils';

export const useSymbolAssetUpload = (newEntry: CatalogFormEntry) => {
  const uploadingCreateAsset = ref(false);
  const uploadingEntryAssetIds = ref<Set<string>>(new Set());

  const pickAndUploadSymbolAsset = async (): Promise<string | null> => {
    const file = await pickFile();
    if (!file) return null;
    const uploaded = await uploadSymbolAsset(file);
    return uploaded.relative_path;
  };

  const pickAndUploadCreateAsset = async (): Promise<void> => {
    if (uploadingCreateAsset.value) return;
    uploadingCreateAsset.value = true;
    try {
      const relativePath = await pickAndUploadSymbolAsset();
      if (!relativePath) return;
      newEntry.reference_assets_json = appendAssetPath(
        newEntry.reference_assets_json,
        relativePath,
      );
      toast.success(`Asset uploaded: ${relativePath}`);
    } catch (error) {
      console.error('Upload symbol asset failed', error);
      toast.error(extractErrorMessage(error, 'Failed to upload symbol asset.'));
    } finally {
      uploadingCreateAsset.value = false;
    }
  };

  const pickAndUploadEntryAsset = async (entry: SymbolRecord): Promise<void> => {
    const next = new Set(uploadingEntryAssetIds.value);
    if (next.has(entry.id)) return;
    next.add(entry.id);
    uploadingEntryAssetIds.value = next;
    try {
      const relativePath = await pickAndUploadSymbolAsset();
      if (!relativePath) return;
      entry.reference_assets_json = appendAssetPath(entry.reference_assets_json, relativePath);
      toast.success(`Asset uploaded: ${relativePath}`);
    } catch (error) {
      console.error('Upload symbol asset failed', error);
      toast.error(extractErrorMessage(error, 'Failed to upload symbol asset.'));
    } finally {
      const done = new Set(uploadingEntryAssetIds.value);
      done.delete(entry.id);
      uploadingEntryAssetIds.value = done;
    }
  };

  return {
    uploadingCreateAsset,
    uploadingEntryAssetIds,
    pickAndUploadCreateAsset,
    pickAndUploadEntryAsset,
  };
};
