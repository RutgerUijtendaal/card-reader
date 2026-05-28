import type { CardHoverTooltipModel } from '@/components/cards/cardModels';

export type DeckMetadataOption = {
  id: string;
  key: string;
  label: string;
};

export type DeckVisibility = 'private' | 'unlisted' | 'public';

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
  visibility: DeckVisibility;
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
    deprecated_card_count?: number;
    deprecated_card_ids?: string[];
  };
  created_at: string;
  updated_at: string;
};

export type DeckEntryInput = {
  card_id: string;
  quantity: number;
};

export type DeckUpsertRequest = {
  name: string;
  description: string | null;
  visibility: DeckVisibility;
  hero_card_id: string;
  entries: DeckEntryInput[];
  sideboards: Array<{
    name: string;
    entries: DeckEntryInput[];
  }>;
};
