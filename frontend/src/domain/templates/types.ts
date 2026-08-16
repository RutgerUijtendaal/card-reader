import type { JsonObject } from '@/shared/types/json';
import type { TemplateParserType } from '@/domain/templates/parserTypes';

export type RegionBounds = {
  unit: 'relative' | 'absolute';
  x: number;
  y: number;
  w: number;
  h: number;
};

export type TemplateRegionDefinition = {
  region_id: string;
  cut_region: RegionBounds;
  parser_type: TemplateParserType;
  ocr_config: JsonObject;
  mana_badge_ocr?: {
    cut_region: RegionBounds;
    scales?: number[];
  };
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
