import { computed, type ComputedRef, type Ref } from 'vue';
import {
  getDeckEntryQuantityLimit,
  getDeckQuantityViolationMessage,
  resolveDeckBuildingRules,
  type DeckConstraintContext,
} from '@/domain/decks/utils/deckConstraints';
import {
  MAX_DECK_COPIES,
  MAX_SIDEBOARD_ENTRY_QUANTITY,
} from '@/domain/decks/utils/constants';
import type { DeckBuildingRules, DeckConstraintScope } from '@/domain/deck-building/types';
import type { DeckCardSummary } from '@/domain/decks/types';
import type {
  DeckBoardMoveDestination,
  DeckForm,
  DeckFormEntry,
} from '@/features/decks/composables/deckEditorDraftTypes';
import { MAINBOARD_ID } from '@/features/decks/composables/useDeckEditorBoards';

type UseDeckEditorConstraintsOptions = {
  form: DeckForm;
  activeBoardId: Ref<string>;
  isHeroStep: ComputedRef<boolean>;
  selectedHero: ComputedRef<DeckCardSummary | null>;
  cardLookup: Ref<Record<string, DeckCardSummary>>;
  baseDeckBuildingRules: Ref<DeckBuildingRules>;
  baseConstraintContext: ComputedRef<Omit<DeckConstraintContext, 'boardId'>>;
  deckBuildingRules: ComputedRef<DeckBuildingRules>;
  totalMainboardCards: ComputedRef<number>;
  overallTotalCards: ComputedRef<number>;
  getEntryQuantity: (cardId: string, boardId?: string) => number;
  getBoardLabel: (boardId: string) => string;
};

export const useDeckEditorConstraints = ({
  form,
  activeBoardId,
  isHeroStep,
  selectedHero,
  cardLookup,
  baseDeckBuildingRules,
  baseConstraintContext,
  deckBuildingRules,
  totalMainboardCards,
  overallTotalCards,
  getEntryQuantity,
  getBoardLabel,
}: UseDeckEditorConstraintsOptions) => {
  const getScopedCardTotal = (scope: DeckConstraintScope): number =>
    scope === 'whole_deck' ? overallTotalCards.value : totalMainboardCards.value;
  const getActionBlockingMainboardCardCountRule = (candidateCard?: DeckCardSummary) => {
    const rules = candidateCard
      ? resolveDeckBuildingRules(baseConstraintContext.value, candidateCard, MAINBOARD_ID)
      : deckBuildingRules.value;
    const rule = rules.mainboard_card_count;
    return rule.severity === 'hard' && rule.blocks_action && rule.max !== undefined ? rule : null;
  };
  const getActionBlockingMainboardMaxCards = (candidateCard?: DeckCardSummary): number =>
    getActionBlockingMainboardCardCountRule(candidateCard)?.max ?? Number.POSITIVE_INFINITY;
  const getActionBlockingMainboardCardTotal = (candidateCard?: DeckCardSummary): number => {
    const rule = getActionBlockingMainboardCardCountRule(candidateCard);
    return rule ? getScopedCardTotal(rule.scope) : totalMainboardCards.value;
  };
  const mainboardMaxCards = computed(() => getActionBlockingMainboardMaxCards());
  const mainboardMaxCardTotal = computed(() => getActionBlockingMainboardCardTotal());

  const getConstraintContext = (boardId = activeBoardId.value): DeckConstraintContext => ({
    ...baseConstraintContext.value,
    boardId,
  });
  const getMoveConstraintContext = (
    cardId: string,
    sourceBoardId: string,
    destinationBoardId: string,
  ): DeckConstraintContext => {
    const removeMovedCopy = (entries: DeckFormEntry[]): DeckFormEntry[] =>
      entries.flatMap((entry) =>
        entry.card_id !== cardId
          ? [entry]
          : entry.quantity <= 1
            ? []
            : [{ ...entry, quantity: entry.quantity - 1 }],
      );
    return {
      mainboardId: MAINBOARD_ID,
      boardId: destinationBoardId,
      heroCard: selectedHero.value,
      cardLookup: cardLookup.value,
      baseRules: baseDeckBuildingRules.value,
      mainboardEntries: sourceBoardId === MAINBOARD_ID ? removeMovedCopy(form.entries) : form.entries,
      sideboards: form.sideboards.map((sideboard) => ({
        ...sideboard,
        entries: sourceBoardId === sideboard.id ? removeMovedCopy(sideboard.entries) : sideboard.entries,
      })),
    };
  };

  const getCardQuantityLimit = (cardId: string, boardId = activeBoardId.value): number => {
    const card = cardLookup.value[cardId];
    if (card) return getDeckEntryQuantityLimit(card, getConstraintContext(boardId)).max;
    return boardId === MAINBOARD_ID
      ? (deckBuildingRules.value.mainboard_copy_limit.max ?? MAX_DECK_COPIES)
      : (deckBuildingRules.value.sideboard_entry_quantity.max ?? MAX_SIDEBOARD_ENTRY_QUANTITY);
  };
  const getCardQuantityLimitMessage = (
    cardId: string,
    boardId = activeBoardId.value,
  ): string => {
    const card = cardLookup.value[cardId];
    if (card) return getDeckEntryQuantityLimit(card, getConstraintContext(boardId)).message;
    const max = getCardQuantityLimit(cardId, boardId);
    return boardId === MAINBOARD_ID
      ? `Mainboard copy limit is ${max}.`
      : `Sideboard copy limit is ${max}.`;
  };
  const isFiniteLimit = (value: number): boolean => Number.isFinite(value);

  const galleryActionLabel = (card: DeckCardSummary): string => {
    if (isHeroStep.value) return form.hero_card_id === card.id ? 'Selected Hero' : 'Use As Hero';
    const boardId = activeBoardId.value;
    const quantity = getEntryQuantity(card.id, boardId);
    const quantityLimit = getDeckEntryQuantityLimit(card, getConstraintContext(boardId)).max;
    if (boardId === MAINBOARD_ID) {
      const maxCards = getActionBlockingMainboardMaxCards(card);
      const cardTotal = getActionBlockingMainboardCardTotal(card);
      if (quantity === 0 && cardTotal >= maxCards) return 'Mainboard Full';
      if (quantity === 0) return 'Add To Mainboard';
      if (quantity >= quantityLimit) return quantityLimit === 1 ? 'At Legendary Limit' : 'At Copy Limit';
      if (cardTotal >= maxCards) return `At Mainboard Limit (${quantity})`;
      return isFiniteLimit(quantityLimit)
        ? `Add Copy (${quantity}/${quantityLimit})`
        : `Add Copy (${quantity})`;
    }
    if (quantity === 0) return 'Add To Sideboard';
    if (quantity >= quantityLimit)
      return quantityLimit === 1 ? 'At Legendary Limit' : 'At Sideboard Limit';
    return `Add Copy (${quantity})`;
  };
  const galleryActionDisabled = (card: DeckCardSummary): boolean => {
    if (isHeroStep.value) return form.hero_card_id === card.id;
    const boardId = activeBoardId.value;
    const quantity = getEntryQuantity(card.id, boardId);
    const atQuantityLimit =
      quantity >= getDeckEntryQuantityLimit(card, getConstraintContext(boardId)).max;
    if (boardId !== MAINBOARD_ID) return atQuantityLimit;
    return (
      atQuantityLimit ||
      (quantity === 0 &&
        getActionBlockingMainboardCardTotal(card) >= getActionBlockingMainboardMaxCards(card))
    );
  };
  const galleryRemoveActionDisabled = (
    cardId: string,
    boardId = activeBoardId.value,
  ): boolean => isHeroStep.value || getEntryQuantity(cardId, boardId) <= 0;
  const boardRowActionDisabled = (cardId: string, boardId = activeBoardId.value): boolean => {
    if (isHeroStep.value) return true;
    const quantity = getEntryQuantity(cardId, boardId);
    if (quantity <= 0) return true;
    return boardId === MAINBOARD_ID
      ? quantity >= getCardQuantityLimit(cardId, boardId) ||
          mainboardMaxCardTotal.value >= mainboardMaxCards.value
      : quantity >= getCardQuantityLimit(cardId, boardId);
  };
  const boardRowSecondaryActionDisabled = (
    cardId: string,
    boardId = activeBoardId.value,
  ): boolean => isHeroStep.value || getEntryQuantity(cardId, boardId) <= 1;

  const getMoveEntryToBoardValidationError = (
    cardId: string,
    destinationBoardId: string,
    sourceBoardId = activeBoardId.value,
  ): string | null => {
    if (isHeroStep.value) return 'Cards cannot be moved during setup.';
    if (destinationBoardId === sourceBoardId) return 'Card is already on that board.';
    if (getEntryQuantity(cardId, sourceBoardId) <= 0) return 'Card is not on the current board.';

    const destinationQuantity = getEntryQuantity(cardId, destinationBoardId);
    const card = cardLookup.value[cardId];
    if (card) {
      const message = getDeckQuantityViolationMessage(
        card,
        destinationQuantity + 1,
        getMoveConstraintContext(cardId, sourceBoardId, destinationBoardId),
      );
      if (message !== null) return message;
    }
    if (destinationBoardId === MAINBOARD_ID) {
      const maxCards = card ? getActionBlockingMainboardMaxCards(card) : mainboardMaxCards.value;
      const cardTotal = card
        ? getActionBlockingMainboardCardTotal(card)
        : mainboardMaxCardTotal.value;
      if (cardTotal + 1 > maxCards) return `Mainboard cannot exceed ${maxCards} cards.`;
    }
    return null;
  };

  const getBoardMoveDestinations = (
    cardId: string,
    sourceBoardId = activeBoardId.value,
  ): DeckBoardMoveDestination[] => {
    if (isHeroStep.value) return [];
    const boardIds = [MAINBOARD_ID, ...form.sideboards.map((sideboard) => sideboard.id)].filter(
      (boardId) => boardId !== sourceBoardId,
    );
    return boardIds.map((boardId) => {
      const error = getMoveEntryToBoardValidationError(cardId, boardId, sourceBoardId);
      return {
        boardId,
        label: getBoardLabel(boardId),
        description: error ?? undefined,
        disabled: error !== null,
      };
    });
  };

  return {
    getActionBlockingMainboardMaxCards,
    getActionBlockingMainboardCardTotal,
    mainboardMaxCards,
    mainboardMaxCardTotal,
    getConstraintContext,
    getCardQuantityLimit,
    getCardQuantityLimitMessage,
    galleryActionLabel,
    galleryActionDisabled,
    galleryRemoveActionDisabled,
    boardRowActionDisabled,
    boardRowSecondaryActionDisabled,
    getMoveEntryToBoardValidationError,
    getBoardMoveDestinations,
  };
};
