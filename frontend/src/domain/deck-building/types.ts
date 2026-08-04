export type DeckConstraintSeverity = 'hard' | 'soft';
export type DeckConstraintScope = 'mainboard' | 'whole_deck';
export type DeckConstraintApplication = 'deck' | 'self';

export type DeckBuildingRule = {
  rule_id: string;
  severity: DeckConstraintSeverity;
  scope: DeckConstraintScope;
  blocks_action: boolean;
  min?: number;
  max?: number;
};

export type DeckBuildingRules = {
  mainboard_copy_limit: DeckBuildingRule;
  mainboard_card_count: DeckBuildingRule;
  mana_type_count: DeckBuildingRule;
  legendary_copy_limit: DeckBuildingRule;
  sideboard_entry_quantity: DeckBuildingRule;
};

export type DeckBuildingRuleOverride = Partial<DeckBuildingRule> & {
  applies_to?: DeckConstraintApplication;
  count?: number;
  minimum?: number;
  maximum?: number;
};

export type DeckBuildingConfig = {
  overrides?: Partial<Record<keyof DeckBuildingRules | string, DeckBuildingRuleOverride>>;
};
