export type KnownCatalogKind = 'keywords' | 'tags' | 'symbols' | 'types';
export type SuggestedCatalogKind = 'suggested-tags' | 'suggested-types';
export type CatalogKind = KnownCatalogKind | SuggestedCatalogKind;

export type CatalogSearchState = Record<CatalogKind, string>;

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export type JsonObject = {
  [key: string]: JsonValue;
};

export type MaintenanceActionResponse = {
  message: string;
  removed_paths: string[];
};

export type OpenStorageLocationResponse = {
  message: string;
  path: string;
};

export type KeywordRecord = {
  id: string;
  key: string;
  label: string;
  identifiers: string[];
  identifiers_text: string;
};

export type TagRecord = {
  id: string;
  key: string;
  label: string;
  identifiers: string[];
  identifiers_text: string;
};

export type TypeRecord = {
  id: string;
  key: string;
  label: string;
  identifiers: string[];
  identifiers_text: string;
};

export type SymbolRecord = {
  id: string;
  key: string;
  label: string;
  symbol_type: string;
  detector_type: SymbolDetectorType;
  detection_config_json: string;
  text_enrichment_json: string;
  reference_assets_json: string;
  text_token: string;
  enabled: boolean;
};

export type TemplateRecord = {
  id: string;
  key: string;
  label: string;
  definition_json: string;
};

export type CatalogResponse = {
  known: {
    keywords: KeywordRecord[];
    tags: TagRecord[];
    symbols: SymbolRecord[];
    types: TypeRecord[];
  };
  suggested: {
    tags: SuggestionRecord[];
    types: SuggestionRecord[];
  };
};

export type SymbolAssetUploadResponse = {
  relative_path: string;
  absolute_path: string;
};

export type SymbolApiRecord = {
  id: string;
  key: string;
  label: string;
  symbol_type: string;
  detector_type: SymbolDetectorType;
  detection_config_json: JsonObject;
  text_enrichment_json: JsonObject;
  reference_assets_json: string[];
  text_token: string;
  enabled: boolean;
};

export type TemplateApiRecord = {
  id: string;
  key: string;
  label: string;
  definition_json: JsonObject;
};

export type CatalogApiResponse = {
  known: {
    keywords: KeywordRecord[];
    tags: TagRecord[];
    symbols: SymbolApiRecord[];
    types: TypeRecord[];
  };
  suggested: {
    tags: SuggestionApiRecord[];
    types: SuggestionApiRecord[];
  };
};

export type KeywordUpsertRequest = {
  label?: string;
  key?: string;
  identifiers?: string[];
};

export type TagUpsertRequest = {
  label?: string;
  key?: string;
  identifiers?: string[];
};

export type TypeUpsertRequest = {
  label?: string;
  key?: string;
  identifiers?: string[];
};

export type SymbolDetectorType = 'template';

export type SymbolDetectorOption = {
  value: SymbolDetectorType;
  label: string;
};

export const SYMBOL_DETECTOR_OPTIONS: SymbolDetectorOption[] = [
  { value: 'template', label: 'Template Match' },
];

export type SymbolUpsertRequest = {
  label?: string;
  key?: string;
  symbol_type?: string;
  detector_type?: SymbolDetectorType;
  detection_config_json?: JsonObject;
  text_enrichment_json?: JsonObject;
  reference_assets_json?: string[];
  text_token?: string;
  enabled?: boolean;
};

export type TemplateUpsertRequest = {
  label?: string;
  key?: string;
  definition_json?: JsonObject;
};

export type SuggestionStatus = 'pending' | 'accepted' | 'rejected';
export type SuggestionKind = 'tag' | 'type';

export type SuggestionOccurrencePreview = {
  card_id: string;
  card_label: string;
  card_version_id: string;
  card_version_name: string;
  source_text: string;
  normalized_source_text: string;
};

export type SuggestionAcceptedTarget = {
  id: string;
  key: string;
  label: string;
  identifiers?: string[];
};

export type SuggestionApiRecord = {
  id: string;
  kind: SuggestionKind;
  display_value: string;
  normalized_value: string;
  status: SuggestionStatus;
  occurrence_count: number;
  accepted_target: SuggestionAcceptedTarget | null;
  occurrences: SuggestionOccurrencePreview[];
};

export type SuggestionRecord = SuggestionApiRecord & {
  label: string;
  key: string;
};

export type CatalogRow = KeywordRecord | TagRecord | TypeRecord | SymbolRecord | SuggestionRecord;

export type CatalogFormEntry = {
  label: string;
  key: string;
  identifiers_text?: string;
  symbol_type: string;
  detector_type: SymbolDetectorType;
  detection_config_json: string;
  text_enrichment_json: string;
  reference_assets_json: string;
  text_token: string;
  enabled: boolean;
};

export type SuggestionAcceptExistingRequest = {
  target_id: string;
};

export type SuggestionAcceptNewRequest = {
  label?: string;
  key?: string;
};
