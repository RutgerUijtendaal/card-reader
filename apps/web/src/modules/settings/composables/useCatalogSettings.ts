import { computed, reactive, ref } from 'vue';
import { toast } from 'vue-sonner';
import {
  createCatalogEntry,
  deleteCatalogEntry,
  fetchCatalog,
  updateCatalogEntry,
  uploadSymbolAsset
} from '@/modules/settings/api/catalog';
import { SYMBOL_DETECTOR_OPTIONS } from '@/modules/settings/types';
import type {
  CatalogFormEntry,
  CatalogKind,
  CatalogRow,
  KeywordRecord,
  KeywordUpsertRequest,
  SymbolRecord,
  SymbolUpsertRequest,
  TagRecord,
  TagUpsertRequest,
  TypeRecord,
  TypeUpsertRequest
} from '@/modules/settings/types';

const CATALOG_KINDS: CatalogKind[] = ['keywords', 'tags', 'symbols', 'types'];

export const kindLabel = (kind: CatalogKind): string => {
  if (kind === 'keywords') return 'Keywords';
  if (kind === 'tags') return 'Tags';
  if (kind === 'symbols') return 'Symbols';
  return 'Types';
};

export const detectionConfigExample =
  '{"threshold":0.9,"scales":[1.0,0.9,1.1],"max_candidates_per_asset":40,"max_detections_per_symbol":8,"nms_iou_threshold":0.25,"center_crop_ratio":0.7}';
export const referenceAssetsExample = '["mana/fire.png","mana/fire_alt.png"]';

export const useCatalogSettings = () => {
  const selectedKind = ref<CatalogKind>('keywords');
  const catalog = reactive<{
    keywords: KeywordRecord[];
    tags: TagRecord[];
    symbols: SymbolRecord[];
    types: TypeRecord[];
  }>({
    keywords: [],
    tags: [],
    symbols: [],
    types: []
  });

  const savingEntryIds = ref<Set<string>>(new Set());
  const deletingEntryIds = ref<Set<string>>(new Set());
  const creatingEntry = ref(false);
  const uploadingCreateAsset = ref(false);
  const uploadingEntryAssetIds = ref<Set<string>>(new Set());
  const advancedEntryIds = ref<Set<string>>(new Set());

  const deleteModal = reactive<{
    open: boolean;
    loading: boolean;
    kind: CatalogKind | null;
    entryId: string | null;
    entryLabel: string;
  }>({
    open: false,
    loading: false,
    kind: null,
    entryId: null,
    entryLabel: ''
  });

  const newEntry = reactive<CatalogFormEntry>({
    label: '',
    key: '',
    symbol_type: 'generic',
    detector_type: 'template',
    detection_config_json: '{}',
    reference_assets_json: '[]',
    text_token: '',
    enabled: true
  });

  const currentRows = computed<CatalogRow[]>(() => catalog[selectedKind.value]);
  const deleteModalMessage = computed(
    () =>
      `Delete "${deleteModal.entryLabel || 'this entry'}"?\n\nThis also removes existing relations from card versions and cannot be undone.`
  );

  const selectKind = (kind: CatalogKind): void => {
    selectedKind.value = kind;
    resetNewEntryForm();
  };

  const isEntryAdvancedOpen = (entryId: string): boolean => advancedEntryIds.value.has(entryId);

  const toggleEntryAdvanced = (entryId: string): void => {
    const next = new Set(advancedEntryIds.value);
    if (next.has(entryId)) {
      next.delete(entryId);
    } else {
      next.add(entryId);
    }
    advancedEntryIds.value = next;
  };

  const loadCatalog = async (): Promise<void> => {
    const data = await fetchCatalog();
    catalog.keywords = data.keywords ?? [];
    catalog.tags = data.tags ?? [];
    catalog.symbols = data.symbols ?? [];
    catalog.types = data.types ?? [];
  };

  const createEntry = async (): Promise<void> => {
    if (creatingEntry.value) return;
    if (!newEntry.label.trim()) {
      toast.error('Label is required.');
      return;
    }

    creatingEntry.value = true;
    const kind = selectedKind.value;

    try {
      if (kind === 'symbols') {
        const payload: SymbolUpsertRequest = {
          label: newEntry.label.trim(),
          key: newEntry.key.trim() || undefined,
          symbol_type: newEntry.symbol_type.trim() || 'generic',
          detector_type: newEntry.detector_type,
          detection_config_json: newEntry.detection_config_json.trim() || '{}',
          reference_assets_json: newEntry.reference_assets_json.trim() || '[]',
          text_token: newEntry.text_token.trim(),
          enabled: newEntry.enabled
        };
        await createCatalogEntry(kind, payload);
      } else {
        const payload: KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest = {
          label: newEntry.label.trim(),
          key: newEntry.key.trim() || undefined
        };
        await createCatalogEntry(kind, payload);
      }

      toast.success('Entry created.');
      resetNewEntryForm();
      await loadCatalog();
    } catch (error) {
      console.error('Create entry failed', error);
      toast.error(extractErrorMessage(error, 'Failed to create entry.'));
    } finally {
      creatingEntry.value = false;
    }
  };

  const setNewEntry = (entry: CatalogFormEntry): void => {
    Object.assign(newEntry, entry);
  };

  const replaceEntry = (kind: CatalogKind, entryId: string, nextEntry: CatalogFormEntry): void => {
    const rows = catalog[kind] as CatalogRow[];
    const index = rows.findIndex((row) => row.id === entryId);
    if (index < 0) return;
    rows[index] = { ...rows[index], ...nextEntry } as CatalogRow;
  };

  const updateEntry = async (kind: CatalogKind, entry: CatalogRow): Promise<void> => {
    const next = new Set(savingEntryIds.value);
    next.add(entry.id);
    savingEntryIds.value = next;

    try {
      if (kind === 'symbols') {
        const symbol = entry as SymbolRecord;
        const payload: SymbolUpsertRequest = {
          label: symbol.label,
          key: symbol.key,
          symbol_type: symbol.symbol_type,
          detector_type: symbol.detector_type,
          detection_config_json: symbol.detection_config_json,
          reference_assets_json: symbol.reference_assets_json,
          text_token: symbol.text_token,
          enabled: symbol.enabled
        };
        await updateCatalogEntry(kind, symbol.id, payload);
      } else {
        const payload: KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest = {
          label: entry.label,
          key: entry.key
        };
        await updateCatalogEntry(kind, entry.id, payload);
      }

      toast.success('Entry updated.');
      await loadCatalog();
    } catch (error) {
      console.error('Update entry failed', error);
      toast.error(extractErrorMessage(error, 'Failed to update entry.'));
    } finally {
      const done = new Set(savingEntryIds.value);
      done.delete(entry.id);
      savingEntryIds.value = done;
    }
  };

  const openDeleteModal = (kind: CatalogKind, entry: CatalogRow): void => {
    if (deletingEntryIds.value.has(entry.id)) return;
    deleteModal.kind = kind;
    deleteModal.entryId = entry.id;
    deleteModal.entryLabel = entry.label?.trim() || entry.key || 'this entry';
    deleteModal.open = true;
  };

  const closeDeleteModal = (): void => {
    if (deleteModal.loading) return;
    deleteModal.open = false;
    deleteModal.kind = null;
    deleteModal.entryId = null;
    deleteModal.entryLabel = '';
  };

  const confirmDeleteEntry = async (): Promise<void> => {
    if (!deleteModal.kind || !deleteModal.entryId) return;
    const kind = deleteModal.kind;
    const entryId = deleteModal.entryId;

    const next = new Set(deletingEntryIds.value);
    if (next.has(entryId)) return;
    next.add(entryId);
    deletingEntryIds.value = next;
    deleteModal.loading = true;

    try {
      await deleteCatalogEntry(kind, entryId);
      toast.success('Entry deleted.');
      closeDeleteModal();
      await loadCatalog();
    } catch (error) {
      console.error('Delete entry failed', error);
      toast.error(extractErrorMessage(error, 'Failed to delete entry.'));
    } finally {
      const done = new Set(deletingEntryIds.value);
      done.delete(entryId);
      deletingEntryIds.value = done;
      deleteModal.loading = false;
    }
  };

  const pickAndUploadCreateAsset = async (): Promise<void> => {
    if (uploadingCreateAsset.value) return;
    uploadingCreateAsset.value = true;
    try {
      const relativePath = await pickAndUploadSymbolAsset();
      if (!relativePath) return;
      newEntry.reference_assets_json = appendAssetPath(newEntry.reference_assets_json, relativePath);
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

  const resetNewEntryForm = (): void => {
    newEntry.label = '';
    newEntry.key = '';
    newEntry.symbol_type = 'generic';
    newEntry.detector_type = 'template';
    newEntry.detection_config_json = '{}';
    newEntry.reference_assets_json = '[]';
    newEntry.text_token = '';
    newEntry.enabled = true;
  };

  return {
    catalogKinds: CATALOG_KINDS,
    selectedKind,
    catalog,
    currentRows,
    newEntry,
    savingEntryIds,
    deletingEntryIds,
    creatingEntry,
      uploadingCreateAsset,
      uploadingEntryAssetIds,
      detectorTypeOptions: SYMBOL_DETECTOR_OPTIONS,
      advancedEntryIds,
    deleteModal,
    deleteModalMessage,
    kindLabel,
    selectKind,
    isEntryAdvancedOpen,
    toggleEntryAdvanced,
    loadCatalog,
    createEntry,
    setNewEntry,
    updateEntry,
    replaceEntry,
    openDeleteModal,
    closeDeleteModal,
    confirmDeleteEntry,
    pickAndUploadCreateAsset,
    pickAndUploadEntryAsset
  };
};

const pickAndUploadSymbolAsset = async (): Promise<string | null> => {
  const file = await pickFile();
  if (!file) return null;
  const uploaded = await uploadSymbolAsset(file);
  return uploaded.relative_path;
};

const pickFile = (): Promise<File | null> =>
  new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff';
    input.onchange = () => {
      const file = input.files?.[0] ?? null;
      resolve(file);
    };
    input.click();
  });

const appendAssetPath = (rawJson: string, path: string): string => {
  let arr: string[] = [];
  try {
    const parsed = JSON.parse(rawJson || '[]');
    if (Array.isArray(parsed)) {
      arr = parsed.filter((item): item is string => typeof item === 'string' && item.trim().length > 0);
    }
  } catch {
    arr = [];
  }

  if (!arr.includes(path)) {
    arr.push(path);
  }
  return JSON.stringify(arr);
};

const extractErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const maybeResponse = (error as { response?: { data?: { detail?: unknown } } }).response;
    const detail = maybeResponse?.data?.detail;
    if (typeof detail === 'string' && detail.length > 0) return detail;
  }
  if (typeof error === 'object' && error && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return fallback;
};
