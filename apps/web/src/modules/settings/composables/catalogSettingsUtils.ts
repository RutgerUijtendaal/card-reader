import type {
  CatalogFormEntry,
  CatalogKind,
  CatalogRow,
  KeywordUpsertRequest,
  SymbolRecord,
  SymbolUpsertRequest,
  TagUpsertRequest,
  TypeUpsertRequest,
} from '@/modules/settings/types';

export const CATALOG_KINDS: CatalogKind[] = ['keywords', 'tags', 'symbols', 'types'];

export const kindLabel = (kind: CatalogKind): string => {
  if (kind === 'keywords') return 'Keywords';
  if (kind === 'tags') return 'Tags';
  if (kind === 'symbols') return 'Symbols';
  return 'Types';
};

export const detectionConfigExample =
  '{"threshold":0.9,"scales":[1.0,0.9,1.1],"max_candidates_per_asset":40,"max_detections_per_symbol":8,"nms_iou_threshold":0.25,"center_crop_ratio":0.7}';
export const referenceAssetsExample = '["mana/fire.png","mana/fire_alt.png"]';

export const createEmptyCatalogEntry = (): CatalogFormEntry => ({
  label: '',
  key: '',
  symbol_type: 'generic',
  detector_type: 'template',
  detection_config_json: detectionConfigExample,
  reference_assets_json: '[]',
  text_token: '',
  enabled: true,
});

export const buildCreatePayload = (
  kind: CatalogKind,
  entry: CatalogFormEntry,
): KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest | SymbolUpsertRequest => {
  if (kind === 'symbols') {
    return {
      label: entry.label.trim(),
      key: entry.key.trim() || undefined,
      symbol_type: entry.symbol_type.trim() || 'generic',
      detector_type: entry.detector_type,
      detection_config_json: entry.detection_config_json.trim() || '{}',
      reference_assets_json: entry.reference_assets_json.trim() || '[]',
      text_token: entry.text_token.trim(),
      enabled: entry.enabled,
    };
  }

  return {
    label: entry.label.trim(),
    key: entry.key.trim() || undefined,
  };
};

export const buildUpdatePayload = (
  kind: CatalogKind,
  entry: CatalogRow,
): KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest | SymbolUpsertRequest => {
  if (kind === 'symbols') {
    const symbol = entry as SymbolRecord;
    return {
      label: symbol.label,
      key: symbol.key,
      symbol_type: symbol.symbol_type,
      detector_type: symbol.detector_type,
      detection_config_json: symbol.detection_config_json,
      reference_assets_json: symbol.reference_assets_json,
      text_token: symbol.text_token,
      enabled: symbol.enabled,
    };
  }

  return {
    label: entry.label,
    key: entry.key,
  };
};

export const pickFile = (): Promise<File | null> =>
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

export const appendAssetPath = (rawJson: string, path: string): string => {
  let arr: string[] = [];
  try {
    const parsed = JSON.parse(rawJson || '[]');
    if (Array.isArray(parsed)) {
      arr = parsed.filter(
        (item): item is string => typeof item === 'string' && item.trim().length > 0,
      );
    }
  } catch {
    arr = [];
  }

  if (!arr.includes(path)) {
    arr.push(path);
  }
  return JSON.stringify(arr);
};

export const extractErrorMessage = (error: unknown, fallback: string): string => {
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
