import type { CardDeckReferenceSummary } from '@/domain/card-deck-references/types';
import type { CardGroupSummary, MetadataGroupName, ScalarFieldName } from '@/domain/cards/types';
import type { CardLifecycleStatus } from '@/domain/cards/utils/filters/cardLifecycle';
import type { CardRole } from '@/domain/cards/cardRoles';
import type { CardFaction } from '@/domain/cards/cardFactions';
import type { CardPool } from '@/domain/cards/cardPools';
import type { ManaFamily } from '@/domain/cards/manaFamilies';
import type { CardBackSelectionFields } from '@/domain/card-backs/types';
import type { CardVersionDetail } from '@/domain/cards/types';

export type CardDetail = CardBackSelectionFields & {
  id: string;
  label: string;
  name: string;
  card_pool: CardPool;
  card_roles: CardRole[];
  card_factions: CardFaction[];
  card_mana_families: ManaFamily[];
  lifecycle_status?: CardLifecycleStatus;
  card_groups: CardGroupSummary[];
  deck_references: CardDeckReferenceSummary[];
};

export type CardDetailVersion = CardVersionDetail & CardBackSelectionFields;

export type MetadataSearchState = Record<MetadataGroupName, string>;

export type EditorForm = {
  name: string;
  type_line: string;
  mana_cost: string;
  attack: string;
  health: string;
  rules_text: string;
  card_pool: CardPool;
  card_roles: CardRole[];
  card_factions: CardFaction[];
  card_mana_families: ManaFamily[];
  deck_building_config: string;
  lifecycle_status: CardLifecycleStatus;
  card_back_override_id?: string | null;
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
