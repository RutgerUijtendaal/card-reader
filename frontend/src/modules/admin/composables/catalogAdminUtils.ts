import type {
  CatalogResponse,
  CatalogFormEntry,
  JsonObject,
  JsonValue,
  CatalogKind,
  CatalogApiResponse,
  CatalogRow,
  KnownCatalogKind,
  KeywordRecord,
  KeywordUpsertRequest,
  SuggestionApiRecord,
  SuggestionRecord,
  SuggestedCatalogKind,
  SymbolRecord,
  SymbolApiRecord,
  SymbolUpsertRequest,
  TagRecord,
  TagUpsertRequest,
  TemplateApiRecord,
  TemplateRecord,
  TypeRecord,
  TypeUpsertRequest,
} from '@/modules/admin/types';

export const KNOWN_CATALOG_KINDS: KnownCatalogKind[] = ['keywords', 'tags', 'symbols', 'types'];
export const SUGGESTED_CATALOG_KINDS: SuggestedCatalogKind[] = ['suggested-tags', 'suggested-types'];
export const CATALOG_KINDS: CatalogKind[] = [...KNOWN_CATALOG_KINDS, ...SUGGESTED_CATALOG_KINDS];
export const CATALOG_KIND_GROUPS = [
  { label: 'Known', kinds: KNOWN_CATALOG_KINDS },
  { label: 'Suggested', kinds: SUGGESTED_CATALOG_KINDS },
] as const;

export const isKnownCatalogKind = (kind: CatalogKind): kind is KnownCatalogKind =>
  KNOWN_CATALOG_KINDS.includes(kind as KnownCatalogKind);

export const isSuggestedCatalogKind = (kind: CatalogKind): kind is SuggestedCatalogKind =>
  SUGGESTED_CATALOG_KINDS.includes(kind as SuggestedCatalogKind);

export const isSuggestionRecord = (row: CatalogRow): row is SuggestionRecord => 'status' in row;

export const kindLabel = (kind: CatalogKind): string => {
  if (kind === 'keywords') return 'Keywords';
  if (kind === 'tags') return 'Tags';
  if (kind === 'symbols') return 'Symbols';
  if (kind === 'types') return 'Types';
  if (kind === 'suggested-tags') return 'Tags';
  return 'Types';
};

export const kindItemLabel = (kind: CatalogKind): string => {
  if (kind === 'keywords') return 'Keyword';
  if (kind === 'tags') return 'Tag';
  if (kind === 'symbols') return 'Symbol';
  if (kind === 'types') return 'Type';
  if (kind === 'suggested-tags') return 'Tag Suggestion';
  return 'Type Suggestion';
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

export const detectionConfigExample = JSON.stringify(
  {
    threshold: 0.9,
    scales: [1.0, 0.9, 1.1],
    max_candidates_per_asset: 40,
    max_detections_per_symbol: 8,
    nms_iou_threshold: 0.25,
    center_crop_ratio: 0.7,
  },
  null,
  2,
);

export const textEnrichmentExample = JSON.stringify(
  {
    ocr_aliases: ['devotion', 'dev0tion'],
    pattern_anchors: ['your devotion to blue', 'devotion to black and red'],
  },
  null,
  2,
);

export const referenceAssetsExample = JSON.stringify(['mana/fire.png', 'mana/fire_alt.png'], null, 2);

export const createEmptyCatalogEntry = (): CatalogFormEntry => ({
  label: '',
  key: '',
  identifiers_text: '',
  symbol_type: 'generic',
  detector_type: 'template',
  detection_config_json: detectionConfigExample,
  text_enrichment_json: JSON.stringify(
    {
      ocr_aliases: [],
      pattern_anchors: [],
    },
    null,
    2,
  ),
  reference_assets_json: '[]',
  text_token: '',
  enabled: true,
});

export const catalogRowToFormEntry = (row: CatalogRow): CatalogFormEntry => {
  if ('status' in row) {
    return createEmptyCatalogEntry();
  }
  if ('symbol_type' in row) {
    return {
      label: row.label,
      key: row.key,
      symbol_type: row.symbol_type,
      detector_type: row.detector_type,
      detection_config_json: row.detection_config_json,
      text_enrichment_json: row.text_enrichment_json,
      reference_assets_json: row.reference_assets_json,
      text_token: row.text_token,
      enabled: row.enabled,
      identifiers_text: '',
    };
  }

  return {
    label: row.label,
    key: row.key,
    identifiers_text: row.identifiers_text,
    symbol_type: 'generic',
    detector_type: 'template',
    detection_config_json: detectionConfigExample,
    text_enrichment_json: '{"ocr_aliases":[],"pattern_anchors":[]}',
    reference_assets_json: '[]',
    text_token: '',
    enabled: true,
  };
};

export const catalogFormEntryToRow = (
  kind: CatalogKind,
  entryId: string,
  entry: CatalogFormEntry,
): CatalogRow => {
  if (isSuggestedCatalogKind(kind)) {
    throw new Error('Suggestions do not use the catalog editor row mapping.');
  }
  if (kind === 'symbols') {
    return {
      id: entryId,
      label: entry.label,
      key: entry.key,
      symbol_type: entry.symbol_type,
      detector_type: entry.detector_type,
      detection_config_json: entry.detection_config_json,
      text_enrichment_json: entry.text_enrichment_json,
      reference_assets_json: entry.reference_assets_json,
      text_token: entry.text_token,
      enabled: entry.enabled,
    };
  }

  return {
    id: entryId,
    label: entry.label,
    key: entry.key,
    identifiers: parseIdentifiersText(entry.identifiers_text ?? ''),
    identifiers_text: entry.identifiers_text ?? '',
  };
};

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
  if (isSuggestedCatalogKind(kind)) {
    throw new Error('Suggestions cannot be created from the catalog editor.');
  }
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
      text_enrichment_json: parseJsonObjectText(
        entry.text_enrichment_json.trim() || '{}',
        'Text enrichment JSON',
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
  if (isSuggestedCatalogKind(kind)) {
    throw new Error('Suggestions cannot be updated from the catalog editor.');
  }
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
      text_enrichment_json: parseJsonObjectText(
        symbol.text_enrichment_json,
        'Text enrichment JSON',
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
  text_enrichment_json: formatJsonText(row.text_enrichment_json, '{}'),
  reference_assets_json: formatJsonText(row.reference_assets_json, '[]'),
});

export const normalizeSuggestionRecord = (row: SuggestionApiRecord): SuggestionRecord => ({
  ...row,
  label: row.display_value,
  key: row.normalized_value,
});

export const normalizeKnownCatalogDetail = (
  kind: KnownCatalogKind,
  row: KeywordRecord | TagRecord | TypeRecord | SymbolApiRecord | SymbolRecord,
): KeywordRecord | TagRecord | TypeRecord | SymbolRecord => {
  if (kind === 'symbols') {
    return normalizeSymbolRecord(row as SymbolApiRecord);
  }

  return {
    ...(row as KeywordRecord | TagRecord | TypeRecord),
    identifiers_text: formatIdentifiersText((row as KeywordRecord | TagRecord | TypeRecord).identifiers ?? []),
  };
};

export const normalizeCatalogResponse = (data: CatalogApiResponse): CatalogResponse => ({
  known: {
    keywords: (data.known?.keywords ?? []).map((row) => ({
      ...row,
      identifiers_text: formatIdentifiersText(row.identifiers ?? []),
    })),
    tags: (data.known?.tags ?? []).map((row) => ({
      ...row,
      identifiers_text: formatIdentifiersText(row.identifiers ?? []),
    })),
    symbols: (data.known?.symbols ?? []).map(normalizeSymbolRecord),
    types: (data.known?.types ?? []).map((row) => ({
      ...row,
      identifiers_text: formatIdentifiersText(row.identifiers ?? []),
    })),
  },
  suggested: {
    tags: (data.suggested?.tags ?? []).map(normalizeSuggestionRecord),
    types: (data.suggested?.types ?? []).map(normalizeSuggestionRecord),
  },
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
