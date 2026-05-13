import type {
  CardHoverTooltipModel,
  CardTooltipSymbolLookup,
} from '@/components/cards/CardHoverTooltip.vue';

export type MetadataOption = {
  id: string;
  key: string;
  label: string;
};

export type SymbolFilterOption = MetadataOption & {
  symbol_type: string;
  text_token: string;
  asset_url: string | null;
};

export type CardFiltersResponse = {
  keywords: MetadataOption[];
  tags: MetadataOption[];
  symbols: SymbolFilterOption[];
  types: MetadataOption[];
};

export type FieldSourceValue = 'auto' | 'manual';

export type FieldSources = {
  fields: Record<'name' | 'type_line' | 'mana_cost' | 'attack' | 'health' | 'rules_text', FieldSourceValue>;
  metadata: Record<'keywords' | 'tags' | 'types' | 'symbols', FieldSourceValue>;
};

export type ParsedSnapshot = {
  fields: {
    name: string;
    type_line: string;
    mana_cost: string;
    attack: number | null;
    health: number | null;
    rules_text: string;
  };
  metadata: {
    keyword_ids: string[];
    tag_ids: string[];
    type_ids: string[];
    symbol_ids: string[];
  };
};

export type ParseResultSummary = {
  id: string;
  created_at: string;
} | null;

export type CardDetail = {
  id: string;
  label: string;
  name: string;
};

export type CardVersionDetail = CardHoverTooltipModel & {
  image_url: string | null;
  editable: boolean;
  keyword_ids: string[];
  tag_ids: string[];
  symbol_ids: string[];
  type_ids: string[];
  field_sources: FieldSources;
  parsed_snapshot: ParsedSnapshot;
  parse_result: ParseResultSummary;
};

export type CardListItem = CardHoverTooltipModel & {
  image_url: string | null;
};

export type PaginatedCardsResponse<TCard = CardListItem> = {
  count: number;
  next_page: number | null;
  previous_page: number | null;
  page: number;
  page_size: number;
  results: TCard[];
};

export type ScalarFieldName = 'name' | 'type_line' | 'mana_cost' | 'attack' | 'health' | 'rules_text';
export type MetadataGroupName = 'keywords' | 'tags' | 'types' | 'symbols';
export type MetadataSearchState = Record<MetadataGroupName, string>;

export type EditorForm = {
  name: string;
  type_line: string;
  mana_cost: string;
  attack: string;
  health: string;
  rules_text: string;
  keyword_ids: string[];
  tag_ids: string[];
  type_ids: string[];
  symbol_ids: string[];
};

export type ScalarFieldConfig = {
  name: ScalarFieldName;
  label: string;
  multiline?: boolean;
};

export type MetadataGroupConfig = {
  name: MetadataGroupName;
  label: string;
};

export const scalarFields: ScalarFieldConfig[] = [
  { name: 'name', label: 'Name' },
  { name: 'type_line', label: 'Type Line' },
  { name: 'mana_cost', label: 'Mana Cost' },
  { name: 'attack', label: 'Attack' },
  { name: 'health', label: 'Health' },
  { name: 'rules_text', label: 'Rules Text', multiline: true },
];

export const metadataGroups: MetadataGroupConfig[] = [
  { name: 'keywords', label: 'Keywords' },
  { name: 'tags', label: 'Tags' },
  { name: 'types', label: 'Types' },
  { name: 'symbols', label: 'Symbols' },
];

export type SymbolLookupMap = Record<string, CardTooltipSymbolLookup>;
