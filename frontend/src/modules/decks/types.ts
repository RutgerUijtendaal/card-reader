import type { CardHoverTooltipModel } from '@/components/cards/cardModels';

export type DeckMetadataOption = {
  id: string;
  key: string;
  label: string;
};

export type DeckCardSummary = CardHoverTooltipModel & {
  result_type?: 'card';
  image_url: string | null;
};

export type DeckEntrySummary = {
  quantity: number;
  card: DeckCardSummary;
};

export type DeckRecord = {
  id: string;
  name: string;
  description: string | null;
  is_public: boolean;
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
  status: {
    is_valid: boolean;
    label: string;
    issues: string[];
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
  is_public: boolean;
  hero_card_id: string;
  entries: DeckEntryInput[];
};
