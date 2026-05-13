import { ref } from 'vue';
import { toast } from 'vue-sonner';
import { uploadSymbolAsset } from '@/modules/settings/api/catalog';
import type { CatalogFormEntry } from '@/modules/settings/types';
import { appendAssetPath, extractErrorMessage, pickFile } from './catalogSettingsUtils';

export const useSymbolAssetUpload = (entry: CatalogFormEntry) => {
  const uploadingAsset = ref(false);

  const pickAndUploadSymbolAsset = async (): Promise<string | null> => {
    const file = await pickFile();
    if (!file) return null;
    const uploaded = await uploadSymbolAsset(file);
    return uploaded.relative_path;
  };

  const pickAndUploadAsset = async (): Promise<void> => {
    if (uploadingAsset.value) return;
    uploadingAsset.value = true;
    try {
      const relativePath = await pickAndUploadSymbolAsset();
      if (!relativePath) return;
      entry.reference_assets_json = appendAssetPath(entry.reference_assets_json, relativePath);
      toast.success(`Asset uploaded: ${relativePath}`);
    } catch (error) {
      console.error('Upload symbol asset failed', error);
      toast.error(extractErrorMessage(error, 'Failed to upload symbol asset.'));
    } finally {
      uploadingAsset.value = false;
    }
  };

  return {
    uploadingAsset,
    pickAndUploadAsset,
  };
};
