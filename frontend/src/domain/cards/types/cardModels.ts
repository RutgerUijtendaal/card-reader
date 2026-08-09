import type { CardLifecycleStatus } from '@/domain/cards/utils/filters/cardLifecycle';
import type { DeckBuildingConfig } from '@/domain/deck-building/types';

export type CardTooltipSymbolLookup = {
  asset_url?: string | null;
  text_token?: string;
};

export type CardTooltipMetadata = {
  id: string;
  key: string;
  label: string;
  linked_card_count?: number;
};

export type CardTooltipSymbol = CardTooltipMetadata & {
  symbol_type: string;
  text_token: string;
  asset_url: string | null;
};

export type CardContentVersionSummary = {
  id: string;
  version_number: string;
  base_version: string;
  description: string;
};

export type CardPool = 'player' | 'game_master';
export type CardRole = 'hero' | 'boon' | 'event';
export type CardRoleFilter = 'standard' | CardRole;

export type CardHoverTooltipModel = {
  id: string;
  key: string;
  label: string;
  card_pool: CardPool;
  card_roles: CardRole[];
  restricted?: boolean;
  deck_building_config?: DeckBuildingConfig;
  lifecycle_status?: CardLifecycleStatus;
  template_id: string;
  version_id: string;
  version_number: number;
  previous_version_id: string | null;
  is_latest: boolean;
  content_version?: CardContentVersionSummary | null;
  name: string;
  type_line: string;
  mana_cost: string;
  mana_symbols: string[];
  mana_value: number | null;
  mana_family_sort_key?: number;
  attack: number | null;
  health: number | null;
  rules_text: string;
  confidence: number;
  created_at: string;
  updated_at: string;
  keywords: string[];
  tags: CardTooltipMetadata[];
  symbols: CardTooltipSymbol[];
  types: CardTooltipMetadata[];
};
