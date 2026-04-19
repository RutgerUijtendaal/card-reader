export type CatalogKind = 'keywords' | 'tags' | 'symbols' | 'types';

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
};

export type TagRecord = {
  id: string;
  key: string;
  label: string;
};

export type TypeRecord = {
  id: string;
  key: string;
  label: string;
};

export type SymbolRecord = {
  id: string;
  key: string;
  label: string;
  symbol_type: string;
  detector_type: SymbolDetectorType;
  detection_config_json: string;
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
  keywords: KeywordRecord[];
  tags: TagRecord[];
  symbols: SymbolRecord[];
  types: TypeRecord[];
};

export type SymbolAssetUploadResponse = {
  relative_path: string;
  absolute_path: string;
};

export type KeywordUpsertRequest = {
  label?: string;
  key?: string;
};

export type TagUpsertRequest = {
  label?: string;
  key?: string;
};

export type TypeUpsertRequest = {
  label?: string;
  key?: string;
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
  detection_config_json?: string;
  reference_assets_json?: string;
  text_token?: string;
  enabled?: boolean;
};

export type TemplateUpsertRequest = {
  label?: string;
  key?: string;
  definition_json?: string;
};

export type CatalogRow = KeywordRecord | TagRecord | TypeRecord | SymbolRecord;

export type CatalogFormEntry = {
  label: string;
  key: string;
  symbol_type: string;
  detector_type: SymbolDetectorType;
  detection_config_json: string;
  reference_assets_json: string;
  text_token: string;
  enabled: boolean;
};
