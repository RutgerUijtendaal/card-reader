import type {
  CatalogResponse,
  CatalogFormEntry,
  CatalogKind,
  CatalogApiResponse,
  CatalogRow,
  DeckTagRecord,
  DeckTagUpsertRequest,
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
  TypeRecord,
  TypeUpsertRequest,
} from '@/features/admin/types';
import type { JsonObject, JsonValue } from '@/shared/types/json';
import { getApiErrorMessageWithCause } from '@/shared/api/errors';

export const KNOWN_CATALOG_KINDS: KnownCatalogKind[] = ['keywords', 'tags', 'symbols', 'types', 'deck-roles', 'deck-types'];
export const SUGGESTED_CATALOG_KINDS: SuggestedCatalogKind[] = ['suggested-tags', 'suggested-types', 'suggested-deck-types'];
export const CLASSIFICATION_CATALOG_KINDS: CatalogKind[] = [
  'card-roles',
  'card-factions',
  'card-mana-families',
];
export const CATALOG_KINDS: CatalogKind[] = [...KNOWN_CATALOG_KINDS, ...SUGGESTED_CATALOG_KINDS, ...CLASSIFICATION_CATALOG_KINDS];
export const CATALOG_KIND_GROUPS = [
  { label: 'Card catalog', kinds: ['keywords', 'tags', 'symbols', 'types', 'suggested-tags', 'suggested-types'] as CatalogKind[] },
  { label: 'Card classification', kinds: ['card-roles', 'card-factions', 'card-mana-families'] as CatalogKind[] },
  { label: 'Deck tags', kinds: ['deck-roles', 'deck-types', 'suggested-deck-types'] as CatalogKind[] },
] as const;

export const isKnownCatalogKind = (kind: CatalogKind): kind is KnownCatalogKind =>
  KNOWN_CATALOG_KINDS.includes(kind as KnownCatalogKind);

export const isSuggestedCatalogKind = (kind: CatalogKind): kind is SuggestedCatalogKind =>
  SUGGESTED_CATALOG_KINDS.includes(kind as SuggestedCatalogKind);

export const isClassificationCatalogKind = (kind: CatalogKind): boolean =>
  kind === 'card-roles' || kind === 'card-factions' || kind === 'card-mana-families';

export const isSuggestionRecord = (row: CatalogRow): row is SuggestionRecord =>
  'status' in row && 'occurrence_count' in row;

export const kindLabel = (kind: CatalogKind): string => {
  if (kind === 'keywords') return 'Keywords';
  if (kind === 'tags') return 'Tags';
  if (kind === 'symbols') return 'Symbols';
  if (kind === 'types') return 'Types';
  if (kind === 'suggested-tags') return 'Suggested tags';
  if (kind === 'suggested-types') return 'Suggested types';
  if (kind === 'card-roles') return 'Card Roles';
  if (kind === 'card-factions') return 'Card Factions';
  if (kind === 'card-mana-families') return 'Mana Families';
  if (kind === 'deck-roles') return 'Roles';
  if (kind === 'deck-types') return 'Types';
  if (kind === 'suggested-deck-types') return 'Suggested types';
  return 'Types';
};

export const kindItemLabel = (kind: CatalogKind): string => {
  if (kind === 'keywords') return 'Keyword';
  if (kind === 'tags') return 'Tag';
  if (kind === 'symbols') return 'Symbol';
  if (kind === 'types') return 'Type';
  if (kind === 'suggested-tags') return 'Tag Suggestion';
  if (kind === 'card-roles') return 'Card Role';
  if (kind === 'card-factions') return 'Card Faction';
  if (kind === 'card-mana-families') return 'Mana Family';
  if (kind === 'deck-roles') return 'Role Tag';
  if (kind === 'deck-types') return 'Type Tag';
  if (kind === 'suggested-deck-types') return 'Type Tag Suggestion';
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
    implied_symbol_keys: [],
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
  if ('target_kind' in row) {
    throw new Error('Classification definitions do not use the generic catalog form.');
  }
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

  if ('kind' in row && !('status' in row)) {
    return {
      ...createEmptyCatalogEntry(),
      label: row.label,
      key: row.key,
      deck_tag_kind: row.kind,
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

  if (kind === 'deck-roles' || kind === 'deck-types') {
    return {
      id: entryId,
      label: entry.label,
      key: entry.key,
      kind: entry.deck_tag_kind ?? (kind === 'deck-roles' ? 'role' : 'type'),
      identifiers: [],
      identifiers_text: '',
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
): KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest | SymbolUpsertRequest | DeckTagUpsertRequest => {
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

  if (kind === 'deck-roles' || kind === 'deck-types') {
    return {
      kind: entry.deck_tag_kind ?? (kind === 'deck-roles' ? 'role' : 'type'),
      label: entry.label.trim(),
      key: entry.key.trim() || undefined,
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
): KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest | SymbolUpsertRequest | DeckTagUpsertRequest => {
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

  if (kind === 'deck-roles' || kind === 'deck-types') {
    const tag = entry as DeckTagRecord;
    return { kind: tag.kind, label: tag.label, key: tag.key };
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
  row: KeywordRecord | TagRecord | TypeRecord | SymbolApiRecord | SymbolRecord | DeckTagRecord,
): KeywordRecord | TagRecord | TypeRecord | SymbolRecord | DeckTagRecord => {
  if (kind === 'symbols') {
    return normalizeSymbolRecord(row as SymbolApiRecord);
  }

  return {
    ...(row as KeywordRecord | TagRecord | TypeRecord | DeckTagRecord),
    identifiers: 'identifiers' in row ? row.identifiers : [],
    identifiers_text: formatIdentifiersText('identifiers' in row ? row.identifiers : []),
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
  classification: {
    roles: data.classification?.roles ?? [],
    factions: data.classification?.factions ?? [],
    mana_families: data.classification?.mana_families ?? [],
  },
});

export const extractErrorMessage = getApiErrorMessageWithCause;
