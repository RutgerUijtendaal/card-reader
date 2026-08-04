import { MAX_DECK_COPIES, MAX_SIDEBOARD_ENTRY_QUANTITY } from '@/domain/decks/utils/constants';
import { fallbackDeckBuildingRules } from '@/domain/decks/utils/deckRules';
import type { DeckMetadataOption } from '@/domain/decks/types';
import type {
  DeckBuildingConfig,
  DeckBuildingRule,
  DeckBuildingRuleOverride,
  DeckBuildingRules,
  DeckConstraintApplication,
  DeckConstraintScope,
  DeckConstraintSeverity,
} from '@/domain/deck-building/types';

export const LEGENDARY_COPY_LIMIT_MESSAGE = 'Legendary cards are limited to 1 copy per deck.';

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
  blocksAction: boolean;
};

type DeckConstraintViolation = {
  ruleId: keyof DeckBuildingRules;
  severity: DeckConstraintSeverity;
  blocksAction: boolean;
  message: string;
};

type RuleApplicationEntry = {
  cardId: string;
  boardId: string;
};

export const isLegendaryCard = (card: DeckConstraintCard | null | undefined): boolean =>
  Boolean(card?.types.some((type) => type.key.trim().toLowerCase() === 'legendary'));

export const resolveDeckBuildingRules = (
  context: Omit<DeckConstraintContext, 'boardId'>,
  candidateCard?: DeckConstraintCard,
  candidateBoardId?: string,
): DeckBuildingRules => {
  let rules = context.baseRules ?? fallbackDeckBuildingRules();
  if (context.heroCard) {
    rules = applyDeckBuildingConfig(rules, context.heroCard.deck_building_config, 'deck');
  }

  const ruleEntries: RuleApplicationEntry[] = [
    ...context.mainboardEntries.map((entry) => ({ cardId: entry.card_id, boardId: context.mainboardId })),
    ...context.sideboards.flatMap((sideboard) =>
      sideboard.entries.map((entry) => ({ cardId: entry.card_id, boardId: sideboard.id })),
    ),
  ];
  if (
    candidateCard
    && candidateBoardId !== undefined
    && !ruleEntries.some((entry) => entry.cardId === candidateCard.id && entry.boardId === candidateBoardId)
  ) {
    ruleEntries.push({ cardId: candidateCard.id, boardId: candidateBoardId });
  }

  const appliedCardIds = new Set<string>();
  const applyCard = (cardId: string): void => {
    appliedCardIds.add(cardId);
    const card = context.cardLookup[cardId];
    if (card) {
      rules = applyDeckBuildingConfig(rules, card.deck_building_config, 'deck');
    }
  };

  for (const entry of sortedRuleEntries(ruleEntries)) {
    applyCard(entry.cardId);
  }
  if (candidateCard && candidateBoardId === undefined && !appliedCardIds.has(candidateCard.id)) {
    rules = applyDeckBuildingConfig(rules, candidateCard.deck_building_config, 'deck');
  }
  return rules;
};

export const getDeckEntryQuantityLimit = (
  card: DeckConstraintCard,
  context: DeckConstraintContext,
): DeckQuantityLimit => {
  const deckRules = resolveDeckBuildingRules(context, card, context.boardId);
  const rules = applySelfDeckBuildingConfig(deckRules, card);
  const boardRule = context.boardId === context.mainboardId
    ? rules.mainboard_copy_limit
    : rules.sideboard_entry_quantity;
  const boardBlocksAction = isActionBlockingRule(boardRule) && boardRule.max !== undefined;
  const boardMax = boardBlocksAction ? boardRule.max as number : Number.POSITIVE_INFINITY;
  const boardMessage = context.boardId === context.mainboardId
    ? `Mainboard copy limit is ${boardRule.max ?? MAX_DECK_COPIES}.`
    : `Sideboard copy limit is ${boardRule.max ?? MAX_SIDEBOARD_ENTRY_QUANTITY}.`;
  const aggregateMainboardCopyLimit = getAggregateMainboardCopyLimit(card.id, context, rules);
  if (aggregateMainboardCopyLimit !== null) {
    const remainingCopies = Math.max(0, aggregateMainboardCopyLimit.max - aggregateMainboardCopyLimit.otherCopies);
    return {
      max: Math.min(boardMax, remainingCopies),
      message: `Mainboard copy limit is ${aggregateMainboardCopyLimit.max}.`,
      blocksAction: true,
    };
  }

  if (
    isLegendaryCard(card)
    && (rules.legendary_copy_limit.scope === 'whole_deck' || context.boardId === context.mainboardId)
    && rules.legendary_copy_limit.severity === 'hard'
    && rules.legendary_copy_limit.blocks_action
    && rules.legendary_copy_limit.max !== undefined
  ) {
    const otherCopies = getCopiesOutsideBoard(card.id, context, rules.legendary_copy_limit.scope);
    return {
      max: Math.min(boardMax, Math.max(0, rules.legendary_copy_limit.max - otherCopies)),
      message: legendaryCopyLimitMessage(rules.legendary_copy_limit.max),
      blocksAction: true,
    };
  }

  return {
    max: boardMax,
    message: boardMessage,
    blocksAction: boardBlocksAction,
  };
};

export const getDeckQuantityViolationMessage = (
  card: DeckConstraintCard,
  quantity: number,
  context: DeckConstraintContext,
): string | null => {
  const limit = getDeckEntryQuantityLimit(card, context);
  if (!limit.blocksAction) {
    return null;
  }
  return quantity > limit.max ? limit.message : null;
};

export const getDeckConstraintMessages = (
  context: Omit<DeckConstraintContext, 'boardId'>,
): string[] => evaluationMessages(evaluateDeckConstraints(context), 'hard');

export const getDeckWarningMessages = (
  context: Omit<DeckConstraintContext, 'boardId'>,
): string[] => evaluationMessages(evaluateDeckConstraints(context), 'soft');

export const getDeckBlockingMessages = (
  context: Omit<DeckConstraintContext, 'boardId'>,
): string[] => [
  ...new Set(
    evaluateDeckConstraints(context)
      .filter((violation) => violation.severity === 'hard' && violation.blocksAction)
      .map((violation) => violation.message),
  ),
];

const evaluateDeckConstraints = (
  context: Omit<DeckConstraintContext, 'boardId'>,
): DeckConstraintViolation[] => {
  const rules = resolveDeckBuildingRules(context);
  const violations: DeckConstraintViolation[] = [];
  const mainboardCardCount = rules.mainboard_card_count;
  const mainboardTotal = scopedEntries(context, mainboardCardCount.scope).reduce((sum, entry) => sum + entry.quantity, 0);
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
  for (const cardId of uniqueEntryCardIds(context)) {
    const cardRules = applySelfDeckBuildingConfig(rules, context.cardLookup[cardId]);
    const mainboardRule = cardRules.mainboard_copy_limit;
    const mainboardMax = mainboardRule.max;
    const mainboardEntries = scopedEntries(context, mainboardRule.scope).filter((entry) => entry.card_id === cardId);
    const mainboardCopyLimitViolated = mainboardRule.scope === 'whole_deck'
      ? hasAggregateQuantityViolation(mainboardEntries, mainboardMax)
      : mainboardEntries.some((entry) => entry.quantity < 1 || (mainboardMax !== undefined && entry.quantity > mainboardMax));
    if (mainboardMax !== undefined && mainboardCopyLimitViolated) {
      violations.push({
        ruleId: 'mainboard_copy_limit',
        severity: mainboardRule.severity,
        blocksAction: mainboardRule.blocks_action,
        message: `Each mainboard card quantity must be between 1 and ${mainboardMax}.`,
      });
    }
  }

  for (const entry of context.sideboards.flatMap((sideboard) => sideboard.entries)) {
    const sideboardRule = applySelfDeckBuildingConfig(rules, context.cardLookup[entry.card_id]).sideboard_entry_quantity;
    const sideboardMax = sideboardRule.max;
    if (sideboardMax !== undefined && (entry.quantity < 1 || entry.quantity > sideboardMax)) {
      violations.push({
        ruleId: 'sideboard_entry_quantity',
        severity: sideboardRule.severity,
        blocksAction: sideboardRule.blocks_action,
        message: `Each sideboard card quantity must be between 1 and ${sideboardMax}.`,
      });
    }
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
  const legendaryCardIds = uniqueEntryCardIds(context).filter((cardId) => {
    const card = context.cardLookup[cardId];
    if (!isLegendaryCard(card)) {
      return false;
    }
    return true;
  });
  for (const cardId of legendaryCardIds) {
    const cardRules = applySelfDeckBuildingConfig(rules, context.cardLookup[cardId]);
    const rule = cardRules.legendary_copy_limit;
    if (rule.max === undefined) {
      continue;
    }
    const total = scopedEntries(context, rule.scope)
      .filter((entry) => entry.card_id === cardId)
      .reduce((sum, entry) => sum + entry.quantity, 0);
    if (total > rule.max) {
      violations.push({
        ruleId: 'legendary_copy_limit',
        severity: rule.severity,
        blocksAction: rule.blocks_action,
        message: legendaryCopyLimitMessage(rule.max),
      });
    }
  }
};

const applyDeckBuildingConfig = (
  rules: DeckBuildingRules,
  config: DeckBuildingConfig | undefined,
  appliesTo: DeckConstraintApplication,
): DeckBuildingRules => {
  const overrides = config?.overrides;
  if (!overrides) {
    return rules;
  }
  return (Object.keys(rules) as Array<keyof DeckBuildingRules>).reduce((nextRules, ruleId) => {
    const override = overrides[ruleId] as DeckBuildingRuleOverride | undefined;
    if (!override || (override.applies_to ?? 'deck') !== appliesTo) {
      return nextRules;
    }
    return {
      ...nextRules,
      [ruleId]: applyRuleOverride(nextRules[ruleId], override),
    };
  }, rules);
};

const applySelfDeckBuildingConfig = (
  rules: DeckBuildingRules,
  card: DeckConstraintCard | null | undefined,
): DeckBuildingRules => applyDeckBuildingConfig(rules, card?.deck_building_config, 'self');

const applyRuleOverride = (
  rule: DeckBuildingRule,
  override: DeckBuildingRuleOverride,
): DeckBuildingRule => ({
  ...rule,
  severity: override.severity === 'hard' || override.severity === 'soft' ? override.severity : rule.severity,
  scope: override.scope === 'mainboard' || override.scope === 'whole_deck' ? override.scope : rule.scope,
  blocks_action: typeof override.blocks_action === 'boolean' ? override.blocks_action : rule.blocks_action,
  min: nonNegativeNumberOrCurrent(getLastDefinedOverride(override, ['min', 'count', 'minimum']), rule.min),
  max: nonNegativeNumberOrCurrent(getLastDefinedOverride(override, ['max', 'maximum']), rule.max),
});

const nonNegativeNumberOrCurrent = (value: unknown, current: number | undefined): number | undefined =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : current;

const getLastDefinedOverride = (
  override: DeckBuildingRuleOverride,
  keys: Array<keyof DeckBuildingRuleOverride>,
): unknown => {
  let value: unknown;
  for (const key of keys) {
    if (Object.prototype.hasOwnProperty.call(override, key)) {
      value = override[key];
    }
  }
  return value;
};

const sortedRuleEntries = (entries: RuleApplicationEntry[]): RuleApplicationEntry[] =>
  [...entries].sort((left, right) => {
    const cardComparison = left.cardId.localeCompare(right.cardId);
    return cardComparison !== 0 ? cardComparison : left.boardId.localeCompare(right.boardId);
  });

const isActionBlockingRule = (rule: DeckBuildingRule): boolean =>
  rule.severity === 'hard' && rule.blocks_action;

const hasAggregateQuantityViolation = (
  entries: DeckConstraintEntry[],
  max: number | undefined,
): boolean => {
  const totals = new Map<string, number>();
  for (const entry of entries) {
    if (entry.quantity < 1) {
      return true;
    }
    totals.set(entry.card_id, (totals.get(entry.card_id) ?? 0) + entry.quantity);
  }
  return max !== undefined && [...totals.values()].some((quantity) => quantity > max);
};

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

const uniqueEntryCardIds = (context: Omit<DeckConstraintContext, 'boardId'>): string[] =>
  [...new Set([
    ...context.mainboardEntries.map((entry) => entry.card_id),
    ...context.sideboards.flatMap((sideboard) => sideboard.entries.map((entry) => entry.card_id)),
  ])].sort((left, right) => left.localeCompare(right));

const getAggregateMainboardCopyLimit = (
  cardId: string,
  context: DeckConstraintContext,
  rules: DeckBuildingRules,
): { max: number; otherCopies: number } | null => {
  const rule = rules.mainboard_copy_limit;
  if (!isActionBlockingRule(rule) || rule.scope !== 'whole_deck' || rule.max === undefined) {
    return null;
  }
  return {
    max: rule.max,
    otherCopies: getCopiesOutsideBoard(cardId, context, rule.scope),
  };
};

const legendaryCopyLimitMessage = (max: number): string =>
  `Legendary cards are limited to ${max} copy per deck.`;

const evaluationMessages = (
  violations: DeckConstraintViolation[],
  severity: DeckConstraintSeverity,
): string[] => [...new Set(violations.filter((violation) => violation.severity === severity).map((violation) => violation.message))];
