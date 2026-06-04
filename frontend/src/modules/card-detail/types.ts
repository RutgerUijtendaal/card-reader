import type { CardHoverTooltipModel, CardTooltipSymbolLookup } from '@/components/cards/cardModels';
import type { CardLifecycleStatus } from '@/modules/card-filters/cardLifecycle';
import type { DeckRecord } from '@/modules/decks/types';

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

export type CardDeckReferenceSummary = DeckRecord & {
  card_reference: {
    is_hero: boolean;
    mainboard_quantity: number;
    sideboard_quantity: number;
  };
};

export type CardDetail = {
  id: string;
  label: string;
  name: string;
  lifecycle_status?: CardLifecycleStatus;
  card_groups: CardGroupSummary[];
  deck_references: CardDeckReferenceSummary[];
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

export type CardGroupMemberDetail = {
  position: number;
  is_anchor: boolean;
  card: CardVersionDetail;
};

export type CardGroupDetail = {
  id: string;
  key: string;
  name: string;
  anchor_card_id: string;
  member_count: number;
  members: CardGroupMemberDetail[];
};

export type PaginatedCardsResponse<TCard = GalleryItem> = {
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
  is_hero: boolean;
  deck_building_config: string;
  lifecycle_status: CardLifecycleStatus;
  keyword_ids: string[];
  tag_ids: string[];
  type_ids: string[];
  additional_symbol_ids: string[];
};

export type ReparseTemplateOption = {
  id: string;
  key: string;
  label: string;
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

export const formatCardContentVersion = (version: Pick<CardVersionDetail, 'content_version'>): string =>
  version.content_version?.version_number ?? 'Unversioned';
