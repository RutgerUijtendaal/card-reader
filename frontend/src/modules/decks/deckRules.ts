import { api } from '@/api/client';
import {
  MAX_DECK_COPIES,
  MAX_MAINBOARD_CARD_COUNT,
  MAX_SIDEBOARD_ENTRY_QUANTITY,
  MIN_MAINBOARD_CARD_COUNT,
  MIN_MAINBOARD_MANA_TYPE_COUNT,
} from '@/modules/decks/constants';
import type { DeckBuildingRules } from '@/modules/decks/deckConstraints';

export type DeckRulesMetadata = {
  supported_rule_ids: string[];
  allowed_severities: Array<'hard' | 'soft'>;
  allowed_scopes: Array<'mainboard' | 'whole_deck'>;
  default_config: { overrides: Record<string, unknown> };
  default_rules: DeckBuildingRules;
  example_config: { overrides: Record<string, unknown> };
};

export const fallbackDeckBuildingDefaultConfig = {
  overrides: {},
};

export const fallbackDeckBuildingRules = (): DeckBuildingRules => ({
  mainboard_copy_limit: {
    rule_id: 'mainboard_copy_limit',
    severity: 'hard',
    scope: 'mainboard',
    blocks_action: true,
    max: MAX_DECK_COPIES,
  },
  mainboard_card_count: {
    rule_id: 'mainboard_card_count',
    severity: 'hard',
    scope: 'mainboard',
    blocks_action: true,
    min: MIN_MAINBOARD_CARD_COUNT,
    max: MAX_MAINBOARD_CARD_COUNT,
  },
  mana_type_count: {
    rule_id: 'mana_type_count',
    severity: 'hard',
    scope: 'mainboard',
    blocks_action: false,
    min: MIN_MAINBOARD_MANA_TYPE_COUNT,
  },
  legendary_copy_limit: {
    rule_id: 'legendary_copy_limit',
    severity: 'soft',
    scope: 'mainboard',
    blocks_action: false,
    max: 1,
  },
  sideboard_entry_quantity: {
    rule_id: 'sideboard_entry_quantity',
    severity: 'hard',
    scope: 'mainboard',
    blocks_action: true,
    max: MAX_SIDEBOARD_ENTRY_QUANTITY,
  },
});

export const fallbackDeckBuildingConfigExample = {
  overrides: {
    mainboard_copy_limit: {
      max: 6,
    },
    mana_type_count: {
      min: 0,
    },
    legendary_copy_limit: {
      severity: 'hard',
      scope: 'whole_deck',
      blocks_action: true,
      max: 1,
    },
  },
};

export const formatDeckBuildingConfigJson = (value: unknown): string =>
  JSON.stringify(value, null, 2);

export const fetchDeckRulesMetadata = async (): Promise<DeckRulesMetadata> => {
  const response = await api.get<DeckRulesMetadata>('/decks/rules');
  return response.data;
};
