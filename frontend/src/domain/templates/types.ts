import type { JsonObject } from '@/shared/types/json';

export type RegionBounds = {
  unit: 'relative' | 'absolute';
  x: number;
  y: number;
  w: number;
  h: number;
};

export type TemplateParserType =
  | 'name_mana_cost'
  | 'type_tag'
  | 'rules_text'
  | 'attack'
  | 'health'
  | 'affinity';

export type TemplateRegionDefinition = {
  region_id: string;
  cut_region: RegionBounds;
  parser_type: TemplateParserType;
  ocr_config: JsonObject;
};

export type TemplateDefinition = JsonObject & {
  id?: string;
  version?: number;
  card_width?: number;
  card_height?: number;
  regions: TemplateRegionDefinition[];
};

export type TemplateRecord = {
  id: string;
  key: string;
  label: string;
  definition_json: string;
};

export type TemplateApiRecord = {
  id: string;
  key: string;
  label: string;
  definition_json: TemplateDefinition;
};

export type TemplateUpsertRequest = {
  label?: string;
  key?: string;
  definition_json?: TemplateDefinition;
};
