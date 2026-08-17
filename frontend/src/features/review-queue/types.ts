import type { PaginatedCardsResponse } from '@/domain/cards/types';
import type { CardPool } from '@/domain/cards/cardPools';
import type { CardRole } from '@/domain/cards/cardRoles';
import type { CardFaction } from '@/domain/cards/cardFactions';
import type { ManaFamily } from '@/domain/cards/manaFamilies';
import type { ParseFlagPropertyKey } from '@/domain/review/types';

export type ReviewView = 'classification' | 'flags';
export type FlagStatus = 'open' | 'resolved' | 'dismissed' | 'all';
export type UserSummary = { id: string; username: string };

export type CardClassificationSnapshot = {
  card_pool: CardPool;
  card_roles: CardRole[];
  card_factions: CardFaction[];
  card_mana_families: ManaFamily[];
};

export type ClassificationReviewItem = {
  id: string;
  status: Exclude<FlagStatus, 'all'>;
  created_at: string;
  updated_at: string;
  review_note: string;
  reviewed_at: string | null;
  reviewed_by: UserSummary | null;
  import_job_id: string;
  import_item_id: string;
  card: {
    id: string | null;
    label: string;
    name: string;
    card_pool: CardPool;
    card_roles: CardRole[];
    card_factions: CardFaction[];
    card_mana_families: ManaFamily[];
    image_url: string | null;
  };
  version: {
    id: string;
    version_number: number;
    is_latest: boolean;
    content_version: { id: string; version_number: string } | null;
  } | null;
  existing_classification: CardClassificationSnapshot;
  inferred_classification: CardClassificationSnapshot;
  inference_evidence: Record<string, unknown>;
};

export type ClassificationReviewPage = PaginatedCardsResponse<ClassificationReviewItem>;

export type ParseFlagReviewItem = {
  id: string;
  flag_id: string;
  status: Exclude<FlagStatus, 'all'>;
  property_key: ParseFlagPropertyKey;
  captured_current_value: string;
  expected_value: string;
  note: string;
  created_at: string;
  updated_at: string;
  review_note: string;
  reviewed_at: string | null;
  reviewed_by: UserSummary | null;
};

export type ParseFlagReviewReport = {
  id: string;
  note: string;
  created_at: string;
  updated_at: string;
  submitted_by: UserSummary;
  card: {
    id: string;
    label: string;
    name: string;
    card_pool: CardPool;
    card_roles: CardRole[];
    card_factions: CardFaction[];
    card_mana_families: ManaFamily[];
    image_url: string | null;
  };
  version: {
    id: string;
    version_number: number;
    is_latest: boolean;
    content_version: { id: string; version_number: string } | null;
  };
  items: ParseFlagReviewItem[];
};

export type ParseFlagPage = PaginatedCardsResponse<ParseFlagReviewReport>;

export type ParseFlagReviewGroup = ParseFlagReviewReport & {
  flagId: string;
  primary: ParseFlagReviewItem;
  openCount: number;
  resolvedCount: number;
  dismissedCount: number;
};
