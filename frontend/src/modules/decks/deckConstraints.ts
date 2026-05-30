import { MAX_DECK_COPIES, MAX_SIDEBOARD_ENTRY_QUANTITY } from '@/modules/decks/constants';
import { fallbackDeckBuildingRules } from '@/modules/decks/deckRules';
import type { DeckMetadataOption } from '@/modules/decks/types';

export const LEGENDARY_COPY_LIMIT_MESSAGE = 'Legendary cards are limited to 1 copy per deck.';

export type DeckConstraintSeverity = 'hard' | 'soft';
export type DeckConstraintScope = 'mainboard' | 'whole_deck';

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

export type DeckBuildingConfig = {
  overrides?: Partial<Record<keyof DeckBuildingRules | string, Partial<DeckBuildingRule> & {
    count?: number;
    minimum?: number;
    maximum?: number;
  }>>;
};
type DeckBuildingRuleOverride = Partial<DeckBuildingRule> & {
  count?: number;
  minimum?: number;
  maximum?: number;
};

export type DeckConstraintCard = {
  id: string;
  types: DeckMetadataOption[];
  deck_building_config?: DeckBuildingConfig;
};

export type DeckConstraintEntry = {
  card_id: string;
  quantity: number;
};

export type DeckConstraintSideboard = {
  id: string;
  entries: DeckConstraintEntry[];
};

export type DeckConstraintContext = {
  mainboardId: string;
  boardId: string;
  heroCard: DeckConstraintCard | null;
  cardLookup: Record<string, DeckConstraintCard>;
  baseRules?: DeckBuildingRules;
  mainboardEntries: DeckConstraintEntry[];
  sideboards: DeckConstraintSideboard[];
};

export type DeckQuantityLimit = {
  max: number;
  message: string;
};

type DeckConstraintViolation = {
  ruleId: keyof DeckBuildingRules;
  severity: DeckConstraintSeverity;
  blocksAction: boolean;
  message: string;
};

export const isLegendaryCard = (card: DeckConstraintCard | null | undefined): boolean =>
  Boolean(card?.types.some((type) => type.key.trim().toLowerCase() === 'legendary'));

export const resolveDeckBuildingRules = (
  context: Omit<DeckConstraintContext, 'boardId'>,
  candidateCard?: DeckConstraintCard,
): DeckBuildingRules => {
  let rules = context.baseRules ?? fallbackDeckBuildingRules();
  if (context.heroCard) {
    rules = applyDeckBuildingConfig(rules, context.heroCard.deck_building_config);
  }

  const seenCardIds = new Set<string>();
  const applyCard = (cardId: string): void => {
    if (seenCardIds.has(cardId)) {
      return;
    }
    seenCardIds.add(cardId);
    const card = context.cardLookup[cardId];
    if (card) {
      rules = applyDeckBuildingConfig(rules, card.deck_building_config);
    }
  };

  for (const entry of context.mainboardEntries) {
    applyCard(entry.card_id);
  }
  for (const sideboard of context.sideboards) {
    for (const entry of sideboard.entries) {
      applyCard(entry.card_id);
    }
  }
  if (candidateCard && !seenCardIds.has(candidateCard.id)) {
    rules = applyDeckBuildingConfig(rules, candidateCard.deck_building_config);
  }
  return rules;
};

export const getDeckEntryQuantityLimit = (
  card: DeckConstraintCard,
  context: DeckConstraintContext,
): DeckQuantityLimit => {
  const rules = resolveDeckBuildingRules(context, card);
  const boardRule = context.boardId === context.mainboardId
    ? rules.mainboard_copy_limit
    : rules.sideboard_entry_quantity;
  const boardMax = boardRule.max ?? (context.boardId === context.mainboardId ? MAX_DECK_COPIES : MAX_SIDEBOARD_ENTRY_QUANTITY);
  const boardMessage = context.boardId === context.mainboardId
    ? `Mainboard copy limit is ${boardMax}.`
    : `Sideboard copy limit is ${boardMax}.`;

  if (
    isLegendaryCard(card)
    && rules.legendary_copy_limit.severity === 'hard'
    && rules.legendary_copy_limit.blocks_action
    && rules.legendary_copy_limit.max !== undefined
  ) {
    const otherCopies = getCopiesOutsideBoard(card.id, context, rules.legendary_copy_limit.scope);
    return {
      max: Math.min(boardMax, Math.max(0, rules.legendary_copy_limit.max - otherCopies)),
      message: legendaryCopyLimitMessage(rules.legendary_copy_limit.max),
    };
  }

  return {
    max: boardMax,
    message: boardMessage,
  };
};

export const getDeckQuantityViolationMessage = (
  card: DeckConstraintCard,
  quantity: number,
  context: DeckConstraintContext,
): string | null => {
  const limit = getDeckEntryQuantityLimit(card, context);
  return quantity > limit.max ? limit.message : null;
};

export const getDeckConstraintMessages = (
  context: Omit<DeckConstraintContext, 'boardId'>,
): string[] => evaluationMessages(evaluateDeckConstraints(context), 'hard');

export const getDeckWarningMessages = (
  context: Omit<DeckConstraintContext, 'boardId'>,
): string[] => evaluationMessages(evaluateDeckConstraints(context), 'soft');

const evaluateDeckConstraints = (
  context: Omit<DeckConstraintContext, 'boardId'>,
): DeckConstraintViolation[] => {
  const rules = resolveDeckBuildingRules(context);
  const violations: DeckConstraintViolation[] = [];
  const mainboardTotal = context.mainboardEntries.reduce((sum, entry) => sum + entry.quantity, 0);
  const mainboardCardCount = rules.mainboard_card_count;
  if (mainboardCardCount.min !== undefined && mainboardTotal < mainboardCardCount.min) {
    violations.push({
      ruleId: 'mainboard_card_count',
      severity: mainboardCardCount.severity,
      blocksAction: false,
      message: `Deck must contain at least ${mainboardCardCount.min} mainboard cards.`,
    });
  }
  if (mainboardCardCount.max !== undefined && mainboardTotal > mainboardCardCount.max) {
    violations.push({
      ruleId: 'mainboard_card_count',
      severity: mainboardCardCount.severity,
      blocksAction: mainboardCardCount.blocks_action,
      message: `Deck cannot contain more than ${mainboardCardCount.max} mainboard cards.`,
    });
  }

  validateEntryQuantities(context, rules, violations);
  validateManaTypeCount(context, rules, violations);
  validateLegendaryCopies(context, rules, violations);
  return violations;
};

const validateEntryQuantities = (
  context: Omit<DeckConstraintContext, 'boardId'>,
  rules: DeckBuildingRules,
  violations: DeckConstraintViolation[],
): void => {
  const mainboardMax = rules.mainboard_copy_limit.max;
  if (mainboardMax !== undefined && context.mainboardEntries.some((entry) => entry.quantity < 1 || entry.quantity > mainboardMax)) {
    violations.push({
      ruleId: 'mainboard_copy_limit',
      severity: rules.mainboard_copy_limit.severity,
      blocksAction: rules.mainboard_copy_limit.blocks_action,
      message: `Each mainboard card quantity must be between 1 and ${mainboardMax}.`,
    });
  }

  const sideboardMax = rules.sideboard_entry_quantity.max;
  if (
    sideboardMax !== undefined
    && context.sideboards.some((sideboard) =>
      sideboard.entries.some((entry) => entry.quantity < 1 || entry.quantity > sideboardMax),
    )
  ) {
    violations.push({
      ruleId: 'sideboard_entry_quantity',
      severity: rules.sideboard_entry_quantity.severity,
      blocksAction: rules.sideboard_entry_quantity.blocks_action,
      message: `Each sideboard card quantity must be between 1 and ${sideboardMax}.`,
    });
  }
};

const validateManaTypeCount = (
  context: Omit<DeckConstraintContext, 'boardId'>,
  rules: DeckBuildingRules,
  violations: DeckConstraintViolation[],
): void => {
  const rule = rules.mana_type_count;
  if (rule.min === undefined) {
    return;
  }
  const entries = scopedEntries(context, rule.scope);
  const manaCount = entries.reduce((sum, entry) => {
    const card = context.cardLookup[entry.card_id];
    return sum + (card?.types.some((type) => type.key.toLowerCase() === 'mana') ? entry.quantity : 0);
  }, 0);
  if (manaCount < rule.min) {
    violations.push({
      ruleId: 'mana_type_count',
      severity: rule.severity,
      blocksAction: rule.blocks_action,
      message: `Deck must contain at least ${rule.min} mainboard cards with type 'Mana'.`,
    });
  }
};

const validateLegendaryCopies = (
  context: Omit<DeckConstraintContext, 'boardId'>,
  rules: DeckBuildingRules,
  violations: DeckConstraintViolation[],
): void => {
  const rule = rules.legendary_copy_limit;
  if (rule.max === undefined) {
    return;
  }
  const max = rule.max;
  const totals = new Map<string, number>();
  for (const entry of scopedEntries(context, rule.scope)) {
    const card = context.cardLookup[entry.card_id];
    if (!isLegendaryCard(card)) {
      continue;
    }
    totals.set(entry.card_id, (totals.get(entry.card_id) ?? 0) + entry.quantity);
  }
  if ([...totals.values()].some((quantity) => quantity > max)) {
    violations.push({
      ruleId: 'legendary_copy_limit',
      severity: rule.severity,
      blocksAction: rule.blocks_action,
      message: legendaryCopyLimitMessage(max),
    });
  }
};

const applyDeckBuildingConfig = (
  rules: DeckBuildingRules,
  config: DeckBuildingConfig | undefined,
): DeckBuildingRules => {
  const overrides = config?.overrides;
  if (!overrides) {
    return rules;
  }
  return (Object.keys(rules) as Array<keyof DeckBuildingRules>).reduce((nextRules, ruleId) => {
    const override = overrides[ruleId] as DeckBuildingRuleOverride | undefined;
    if (!override) {
      return nextRules;
    }
    return {
      ...nextRules,
      [ruleId]: applyRuleOverride(nextRules[ruleId], override),
    };
  }, rules);
};

const applyRuleOverride = (
  rule: DeckBuildingRule,
  override: DeckBuildingRuleOverride,
): DeckBuildingRule => ({
  ...rule,
  severity: override.severity === 'hard' || override.severity === 'soft' ? override.severity : rule.severity,
  scope: override.scope === 'mainboard' || override.scope === 'whole_deck' ? override.scope : rule.scope,
  blocks_action: typeof override.blocks_action === 'boolean' ? override.blocks_action : rule.blocks_action,
  min: nonNegativeNumberOrCurrent(override.min ?? override.count ?? override.minimum, rule.min),
  max: nonNegativeNumberOrCurrent(override.max ?? override.maximum, rule.max),
});

const nonNegativeNumberOrCurrent = (value: unknown, current: number | undefined): number | undefined =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : current;

const scopedEntries = (
  context: Omit<DeckConstraintContext, 'boardId'>,
  scope: DeckConstraintScope,
): DeckConstraintEntry[] => {
  if (scope === 'whole_deck') {
    return [
      ...context.mainboardEntries,
      ...context.sideboards.flatMap((sideboard) => sideboard.entries),
    ];
  }
  return context.mainboardEntries;
};

const getCopiesOutsideBoard = (
  cardId: string,
  context: DeckConstraintContext,
  scope: DeckConstraintScope,
): number => {
  let count = 0;
  if (context.boardId !== context.mainboardId) {
    count += getEntryQuantity(context.mainboardEntries, cardId);
  }
  if (scope === 'whole_deck') {
    for (const sideboard of context.sideboards) {
      if (sideboard.id !== context.boardId) {
        count += getEntryQuantity(sideboard.entries, cardId);
      }
    }
  }
  return count;
};

const getEntryQuantity = (entries: DeckConstraintEntry[], cardId: string): number =>
  entries.find((entry) => entry.card_id === cardId)?.quantity ?? 0;

const legendaryCopyLimitMessage = (max: number): string =>
  `Legendary cards are limited to ${max} copy per deck.`;

const evaluationMessages = (
  violations: DeckConstraintViolation[],
  severity: DeckConstraintSeverity,
): string[] => [...new Set(violations.filter((violation) => violation.severity === severity).map((violation) => violation.message))];
