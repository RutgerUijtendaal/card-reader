import type { CardHoverTooltipModel } from '@/domain/cards/types/cardModels';
import type { DeckBuildingRules } from '@/domain/deck-building/types';

export type DeckMetadataOption = {
  id: string;
  key: string;
  label: string;
};

export type DeckTagKind = 'role' | 'type';

export type DeckTagOption = DeckMetadataOption & {
  kind: DeckTagKind;
};

export type PendingDeckTagSuggestion = {
  id: string;
  label: string;
  normalized_value: string;
  kind: 'type';
  status: 'pending';
};

export type DeckTagCatalog = {
  roles: DeckTagOption[];
  types: DeckTagOption[];
};

export type DeckTagSuggestionResult = {
  label: string;
  normalized_value: string;
  status: 'pending' | 'resolved' | 'rejected';
  message: string | null;
  suggestion_id: string | null;
  tag: DeckTagOption | null;
};

export type DeckVisibility = 'private' | 'unlisted' | 'public';
export type DeckDifficulty = 'easy' | 'medium' | 'hard';

export type DeckCardSummary = CardHoverTooltipModel & {
  result_type: 'card';
  image_url: string | null;
};

export type DeckEntrySummary = {
  quantity: number;
  card: DeckCardSummary;
};

export type DeckSideboardRecord = {
  id: string;
  name: string;
  total_cards: number;
  unique_cards: number;
  entries: DeckEntrySummary[];
};

export type DeckRecord = {
  id: string;
  name: string;
  description: string | null;
  long_description: string | null;
  difficulty: DeckDifficulty | null;
  visibility: DeckVisibility;
  tags?: DeckTagOption[];
  pending_tag_suggestions?: PendingDeckTagSuggestion[];
  tag_suggestion_results?: DeckTagSuggestionResult[];
  owner: {
    id: string;
    username: string;
  };
  hero_card: DeckCardSummary;
  mainboard: {
    total_cards: number;
    unique_cards: number;
    entries: DeckEntrySummary[];
  };
  sideboards: DeckSideboardRecord[];
  totals: {
    overall_total_cards: number;
    overall_unique_cards: number;
    mainboard_total_cards: number;
    mainboard_unique_cards: number;
  };
  status: {
    is_valid: boolean;
    label: string;
    issues: string[];
    warnings?: string[];
    deprecated_card_count?: number;
    deprecated_card_ids?: string[];
  };
  deck_building_rules?: DeckBuildingRules;
  created_at: string;
  updated_at: string;
};

export type DeckHeroSummary = Pick<DeckCardSummary, 'id' | 'key' | 'label' | 'name' | 'image_url' | 'symbols'>;

export type DeckSummaryRecord = {
  id: string;
  name: string;
  description: string | null;
  difficulty: DeckDifficulty | null;
  visibility: DeckVisibility;
  tags?: DeckTagOption[];
  pending_tag_suggestions?: PendingDeckTagSuggestion[];
  owner: {
    id: string;
    username: string;
  };
  hero_card: DeckHeroSummary;
  mainboard: {
    total_cards: number;
    unique_cards: number;
  };
  sideboard_count: number;
  status: {
    is_valid: boolean;
    label: string;
    deprecated_card_count?: number;
  };
  created_at: string;
  updated_at: string;
};

export type DeckListRecord = DeckRecord | DeckSummaryRecord;

export type DeckEntryInput = {
  card_id: string;
  quantity: number;
};

export type DeckUpsertRequest = {
  name: string;
  description: string | null;
  long_description: string | null;
  difficulty: DeckDifficulty | null;
  visibility: DeckVisibility;
  hero_card_id: string;
  entries: DeckEntryInput[];
  sideboards: Array<{
    name: string;
    entries: DeckEntryInput[];
  }>;
  tag_ids: string[];
  suggested_type_labels: string[];
};

export type DeckUpdateRequest = Partial<DeckUpsertRequest>;
