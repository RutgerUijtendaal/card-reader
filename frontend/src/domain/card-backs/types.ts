import type { CardPool } from '@/domain/cards/cardPools';
import type { CardFaction } from '@/domain/cards/cardFactions';
import type { CardRole } from '@/domain/cards/cardRoles';

export type CardBackRecord = {
  id: string;
  label: string;
  original_filename: string;
  source_file: string;
  stored_path: string;
  width: number;
  height: number;
  checksum: string;
  default_for_pools: CardPool[];
  default_for_factions: CardFaction[];
  default_for_roles: CardRole[];
  override_card_count: number;
  is_usable: boolean;
  image_url: string | null;
  created_at: string;
  updated_at: string;
};

export type PublicCardBackRecord = Pick<
  CardBackRecord,
  'id' | 'label' | 'width' | 'height' | 'image_url' | 'created_at' | 'updated_at'
>;

export type CardBackCurrentResponse = {
  current: PublicCardBackRecord | null;
};

export type CardBackDefaults = Record<CardPool, PublicCardBackRecord | null>;

export type CardBackFactionDefaults = Record<CardFaction, PublicCardBackRecord | null>;

export type CardBackRoleDefaults = Record<CardRole, PublicCardBackRecord | null>;

export type ResolvedCardBackPayload = (
  | {
    source: 'override' | 'pool_default';
    asset: PublicCardBackRecord;
  }
  | {
    source: 'faction_default';
    faction: CardFaction;
    asset: PublicCardBackRecord;
  }
  | {
    source: 'role_default';
    role: CardRole;
    asset: PublicCardBackRecord;
  }
) | null;

export type CardBackSelectionFields = {
  card_back_override_id: string | null;
  effective_card_back: ResolvedCardBackPayload;
};
