import type { CardHoverTooltipModel, CardTooltipSymbolLookup } from '@/domain/cards/types/cardModels';

export type ScalarFieldName = 'name' | 'type_line' | 'mana_cost' | 'attack' | 'health' | 'rules_text';
export type MetadataGroupName = 'keywords' | 'tags' | 'types' | 'symbols';

export type MetadataOption = {
  id: string;
  key: string;
  label: string;
  linked_card_count?: number;
};

export type SymbolFilterOption = MetadataOption & {
  symbol_type: string;
  text_token: string;
  asset_url: string | null;
};

export type ManaFamilyOption = {
  key: string;
  label: string;
  rank: number;
  mana_symbol: SymbolFilterOption | null;
  affinity_symbol: SymbolFilterOption | null;
};

export type CardFiltersResponse = {
  keywords: MetadataOption[];
  tags: MetadataOption[];
  symbols: SymbolFilterOption[];
  types: MetadataOption[];
  mana_families?: ManaFamilyOption[];
};

export type FieldSourceValue = 'auto' | 'manual';

export type FieldSources = {
  fields: Record<ScalarFieldName, FieldSourceValue>;
  metadata: Record<MetadataGroupName, FieldSourceValue>;
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

export type CardGroupSummary = {
  id: string;
  key: string;
  name: string;
  anchor_card_id: string;
  member_count: number;
  card_ids: string[];
  is_anchor: boolean;
  position: number | null;
};

export type CardVersionDetail = CardHoverTooltipModel & {
  image_url: string | null;
  editable: boolean;
  rules_text_enriched: string;
  keyword_ids: string[];
  tag_ids: string[];
  symbol_ids: string[];
  type_ids: string[];
  field_sources: FieldSources;
  parsed_snapshot: ParsedSnapshot;
  parse_result: ParseResultSummary;
};

export type CardListItem = CardHoverTooltipModel & {
  result_type: 'card';
  image_url: string | null;
};

export type CardGroupPreviewCard = {
  card_id: string;
  position: number;
  name: string;
  image_url: string | null;
};

export type CardGroupGalleryItem = {
  id: string;
  result_type: 'card_group';
  group_id: string;
  group_key: string;
  group_name: string;
  anchor_card_id: string;
  anchor_card_name: string;
  member_count: number;
  preview_cards: CardGroupPreviewCard[];
};

export type GalleryItem = CardListItem | CardGroupGalleryItem;

export type PaginatedCardsResponse<TCard = GalleryItem> = {
  count: number;
  next_page: number | null;
  previous_page: number | null;
  page: number;
  page_size: number;
  results: TCard[];
};

export type SymbolLookupMap = Record<string, CardTooltipSymbolLookup>;

export const formatCardContentVersion = (version: Pick<CardVersionDetail, 'content_version'>): string =>
  version.content_version?.version_number ?? 'Unversioned';
