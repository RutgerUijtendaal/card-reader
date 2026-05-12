import type {
  CatalogResponse,
  CatalogFormEntry,
  JsonObject,
  JsonValue,
  CatalogKind,
  CatalogApiResponse,
  CatalogRow,
  KeywordRecord,
  KeywordUpsertRequest,
  SymbolRecord,
  SymbolApiRecord,
  SymbolUpsertRequest,
  TagUpsertRequest,
  TemplateApiRecord,
  TemplateRecord,
  TypeUpsertRequest,
} from '@/modules/settings/types';

export const CATALOG_KINDS: CatalogKind[] = ['keywords', 'tags', 'symbols', 'types'];

export const kindLabel = (kind: CatalogKind): string => {
  if (kind === 'keywords') return 'Keywords';
  if (kind === 'tags') return 'Tags';
  if (kind === 'symbols') return 'Symbols';
  return 'Types';
};

export const formatIdentifiersText = (identifiers: string[]): string =>
  identifiers.filter((item) => item.trim().length > 0).join('\n');

export const formatJsonText = (value: JsonValue, fallback: string): string => {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return fallback;
  }
};

export const parseIdentifiersText = (rawText: string): string[] => {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const segment of rawText.split(/\r?\n|,/)) {
    const normalized = segment.trim().toLowerCase();
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    out.push(normalized);
  }
  return out;
};

export const detectionConfigExample =
  '{"threshold":0.9,"scales":[1.0,0.9,1.1],"max_candidates_per_asset":40,"max_detections_per_symbol":8,"nms_iou_threshold":0.25,"center_crop_ratio":0.7}';
export const referenceAssetsExample = '["mana/fire.png","mana/fire_alt.png"]';

export const createEmptyCatalogEntry = (): CatalogFormEntry => ({
  label: '',
  key: '',
  identifiers_text: '',
  symbol_type: 'generic',
  detector_type: 'template',
  detection_config_json: detectionConfigExample,
  reference_assets_json: '[]',
  text_token: '',
  enabled: true,
});

const parseJsonText = (rawText: string, fieldLabel: string): JsonValue => {
  const trimmed = rawText.trim();
  if (!trimmed) {
    throw new Error(`${fieldLabel} is required.`);
  }
  try {
    return JSON.parse(trimmed) as JsonValue;
  } catch {
    throw new Error(`${fieldLabel} must be valid JSON.`);
  }
};

const parseJsonObjectText = (rawText: string, fieldLabel: string): JsonObject => {
  const parsed = parseJsonText(rawText, fieldLabel);
  if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
    throw new Error(`${fieldLabel} must be a JSON object.`);
  }
  return parsed;
};

const parseStringArrayText = (rawText: string, fieldLabel: string): string[] => {
  const parsed = parseJsonText(rawText, fieldLabel);
  if (!Array.isArray(parsed)) {
    throw new Error(`${fieldLabel} must be a JSON array.`);
  }
  if (!parsed.every((item) => typeof item === 'string')) {
    throw new Error(`${fieldLabel} entries must be strings.`);
  }
  return parsed;
};

export const buildCreatePayload = (
  kind: CatalogKind,
  entry: CatalogFormEntry,
): KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest | SymbolUpsertRequest => {
  if (kind === 'keywords') {
    return {
      label: entry.label.trim(),
      key: entry.key.trim() || undefined,
      identifiers: parseIdentifiersText(entry.identifiers_text ?? ''),
    };
  }

  if (kind === 'symbols') {
    return {
      label: entry.label.trim(),
      key: entry.key.trim() || undefined,
      symbol_type: entry.symbol_type.trim() || 'generic',
      detector_type: entry.detector_type,
      detection_config_json: parseJsonObjectText(
        entry.detection_config_json.trim() || '{}',
        'Detection config JSON',
      ),
      reference_assets_json: parseStringArrayText(
        entry.reference_assets_json.trim() || '[]',
        'Reference assets JSON',
      ),
      text_token: entry.text_token.trim(),
      enabled: entry.enabled,
    };
  }

  return {
    label: entry.label.trim(),
    key: entry.key.trim() || undefined,
    identifiers: parseIdentifiersText(entry.identifiers_text ?? ''),
  };
};

export const buildUpdatePayload = (
  kind: CatalogKind,
  entry: CatalogRow,
): KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest | SymbolUpsertRequest => {
  if (kind === 'keywords' || kind === 'tags' || kind === 'types') {
    const keyword = entry as KeywordRecord;
    return {
      label: keyword.label,
      key: keyword.key,
      identifiers: parseIdentifiersText(keyword.identifiers_text),
    };
  }

  if (kind === 'symbols') {
    const symbol = entry as SymbolRecord;
    return {
      label: symbol.label,
      key: symbol.key,
      symbol_type: symbol.symbol_type,
      detector_type: symbol.detector_type,
      detection_config_json: parseJsonObjectText(
        symbol.detection_config_json,
        'Detection config JSON',
      ),
      reference_assets_json: parseStringArrayText(
        symbol.reference_assets_json,
        'Reference assets JSON',
      ),
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

const normalizeSymbolRecord = (row: SymbolApiRecord): SymbolRecord => ({
  ...row,
  detection_config_json: formatJsonText(row.detection_config_json, '{}'),
  reference_assets_json: formatJsonText(row.reference_assets_json, '[]'),
});

export const normalizeCatalogResponse = (data: CatalogApiResponse): CatalogResponse => ({
  keywords: (data.keywords ?? []).map((row) => ({
    ...row,
    identifiers_text: formatIdentifiersText(row.identifiers ?? []),
  })),
  tags: (data.tags ?? []).map((row) => ({
    ...row,
    identifiers_text: formatIdentifiersText(row.identifiers ?? []),
  })),
  symbols: (data.symbols ?? []).map(normalizeSymbolRecord),
  types: (data.types ?? []).map((row) => ({
    ...row,
    identifiers_text: formatIdentifiersText(row.identifiers ?? []),
  })),
});

export const normalizeTemplateRecord = (row: TemplateApiRecord): TemplateRecord => ({
  ...row,
  definition_json: formatJsonText(row.definition_json, '{}'),
});

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
