import { computed, reactive, ref, type Ref } from 'vue';
import type { CardListItem } from '@/domain/cards/types';
import { getDeckEntryQuantityLimit } from '@/domain/decks/utils/deckConstraints';
import type { DeckBuildingRules } from '@/domain/deck-building/types';
import { fallbackDeckBuildingRules } from '@/domain/decks/utils/deckRules';
import type {
  DeckCardSummary,
  DeckDifficulty,
  DeckRecord,
  DeckVisibility,
} from '@/domain/decks/types';
import type {
  DeckEditorMode,
  DeckForm,
} from '@/features/decks/composables/deckEditorDraftTypes';
import {
  buildDeckCardLookup,
  buildDeckUpsertPayload,
  createEmptyDeckForm,
  hydrateDeckForm,
} from '@/features/decks/composables/deckEditorDraftModel';
import {
  MAINBOARD_ID,
  useDeckEditorBoards,
} from '@/features/decks/composables/useDeckEditorBoards';
import { useDeckEditorMetrics } from '@/features/decks/composables/useDeckEditorMetrics';
import { useDeckEditorConstraints } from '@/features/decks/composables/useDeckEditorConstraints';

type UseDeckEditorDraftOptions = {
  editorMode: Ref<DeckEditorMode>;
  cardLookup: Ref<Record<string, DeckCardSummary>>;
  deckBuildingRules?: Ref<DeckBuildingRules>;
  rememberCards: (cards: CardListItem[]) => void;
};

export const useDeckEditorDraft = ({
  editorMode,
  cardLookup,
  deckBuildingRules: baseDeckBuildingRules,
  rememberCards,
}: UseDeckEditorDraftOptions) => {
  const effectiveBaseDeckBuildingRules = baseDeckBuildingRules ?? ref(fallbackDeckBuildingRules());
  const form = reactive(createEmptyDeckForm());
  const isHeroStep = computed(() => editorMode.value === 'hero');
  const isDetailsStep = computed(() => editorMode.value === 'details');
  const isCardsStep = computed(() => editorMode.value === 'cards');
  const selectedHero = computed(() =>
    form.hero_card_id ? cardLookup.value[form.hero_card_id] ?? null : null,
  );

  const boards = useDeckEditorBoards(form);
  const metrics = useDeckEditorMetrics({
    form,
    cardLookup,
    selectedHero,
    baseDeckBuildingRules: effectiveBaseDeckBuildingRules,
    visibleActiveBoardEntries: boards.visibleActiveBoardEntries,
  });
  const constraints = useDeckEditorConstraints({
    form,
    activeBoardId: boards.activeBoardId,
    isHeroStep,
    selectedHero,
    cardLookup,
    baseDeckBuildingRules: effectiveBaseDeckBuildingRules,
    baseConstraintContext: metrics.baseConstraintContext,
    deckBuildingRules: metrics.deckBuildingRules,
    totalMainboardCards: metrics.totalMainboardCards,
    overallTotalCards: metrics.overallTotalCards,
    getEntryQuantity: boards.getEntryQuantity,
    getBoardLabel: boards.getBoardLabel,
  });

  const setDeckName = (value: string): void => {
    form.name = value;
  };
  const setDeckDescription = (value: string): void => {
    form.description = value;
  };
  const setDeckLongDescription = (value: string): void => {
    form.long_description = value;
  };
  const setDeckDifficulty = (value: DeckDifficulty | null): void => {
    form.difficulty = value;
  };
  const setDeckVisibility = (value: DeckVisibility): void => {
    form.visibility = value;
  };
  const setDeckTagIds = (tagIds: string[]): void => {
    form.tag_ids = [...new Set(tagIds)];
  };
  const setSuggestedTypeLabels = (labels: string[]): void => {
    form.suggested_type_labels = [...new Set(labels.map((label) => label.trim()).filter(Boolean))];
  };

  const hydrateFromDeck = (deck: DeckRecord): void => {
    boards.clearPendingRemovedEntries();
    hydrateDeckForm(form, deck);
    boards.activeBoardId.value = MAINBOARD_ID;
    cardLookup.value = buildDeckCardLookup(cardLookup.value, deck);
  };
  const hydrateFromLocalDraft = (draftForm: DeckForm): void => {
    boards.clearPendingRemovedEntries();
    Object.assign(form, {
      ...draftForm,
      entries: draftForm.entries.map((entry) => ({ ...entry })),
      sideboards: draftForm.sideboards.map((sideboard) => ({
        ...sideboard,
        entries: sideboard.entries.map((entry) => ({ ...entry })),
      })),
      tag_ids: [...draftForm.tag_ids],
      suggested_type_labels: [...draftForm.suggested_type_labels],
    });
    boards.activeBoardId.value = MAINBOARD_ID;
  };
  const resetLocalDraft = (): void => {
    hydrateFromLocalDraft(createEmptyDeckForm());
  };
  const buildPayload = () => buildDeckUpsertPayload(form);

  const changeQuantity = (
    cardId: string,
    delta: number,
    boardId = boards.activeBoardId.value,
  ): void => {
    const boardEntries = boards.getBoardEntries(boardId);
    const currentQuantity = boards.getEntryQuantity(cardId, boardId);
    boards.updateBoardEntries(
      boardId,
      boardEntries.map((entry) => {
        if (entry.card_id !== cardId) return entry;
        const limit = constraints.getCardQuantityLimit(cardId, boardId);
        return { ...entry, quantity: Math.max(1, Math.min(limit, entry.quantity + delta)) };
      }),
    );
    if (currentQuantity > 0 && delta !== 0) {
      boards.notifyBoardEntryChange(cardId, boardId, delta > 0 ? 'add' : 'remove');
    }
  };

  const setQuantity = (
    cardId: string,
    rawValue: string,
    boardId = boards.activeBoardId.value,
  ): void => {
    const parsed = Number.parseInt(rawValue, 10);
    const limit = constraints.getCardQuantityLimit(cardId, boardId);
    const quantity = Number.isNaN(parsed) ? 1 : Math.max(1, Math.min(limit, parsed));
    boards.updateBoardEntries(
      boardId,
      boards
        .getBoardEntries(boardId)
        .map((entry) => (entry.card_id === cardId ? { ...entry, quantity } : entry)),
    );
  };

  const addEntry = (card: CardListItem): void => {
    rememberCards([card]);
    const boardId = boards.activeBoardId.value;
    boards.clearPendingRemovedEntry(card.id, boardId);
    const currentQuantity = boards.getEntryQuantity(card.id, boardId);
    const quantityLimit = getDeckEntryQuantityLimit(
      card,
      constraints.getConstraintContext(boardId),
    ).max;
    if (boardId === MAINBOARD_ID) {
      const maxCards = constraints.getActionBlockingMainboardMaxCards(card);
      const cardTotal = constraints.getActionBlockingMainboardCardTotal(card);
      if (currentQuantity >= quantityLimit || cardTotal >= maxCards) return;
      form.entries =
        currentQuantity === 0
          ? [...form.entries, { card_id: card.id, quantity: 1 }]
          : form.entries.map((entry) =>
              entry.card_id === card.id
                ? { ...entry, quantity: Math.min(quantityLimit, entry.quantity + 1) }
                : entry,
            );
      boards.notifyBoardEntryChange(card.id, boardId, 'add');
      return;
    }

    const boardEntries = boards.getBoardEntries(boardId);
    if (currentQuantity >= quantityLimit) return;
    boards.updateBoardEntries(
      boardId,
      currentQuantity === 0
        ? [...boardEntries, { card_id: card.id, quantity: 1 }]
        : boardEntries.map((entry) =>
            entry.card_id === card.id
              ? { ...entry, quantity: Math.min(quantityLimit, entry.quantity + 1) }
              : entry,
          ),
    );
    boards.notifyBoardEntryChange(card.id, boardId, 'add');
  };

  const handleGalleryAction = (card: CardListItem): void => {
    if (isHeroStep.value) {
      rememberCards([card]);
      form.hero_card_id = card.id;
    } else addEntry(card);
  };
  const handleGalleryRemoveAction = (
    cardId: string,
    boardId = boards.activeBoardId.value,
  ): void => {
    if (constraints.galleryRemoveActionDisabled(cardId, boardId)) return;
    if (boards.getEntryQuantity(cardId, boardId) <= 1) boards.removeEntry(cardId, boardId);
    else changeQuantity(cardId, -1, boardId);
  };
  const handleBoardRowAction = (
    cardId: string,
    boardId = boards.activeBoardId.value,
  ): void => {
    if (!constraints.boardRowActionDisabled(cardId, boardId)) changeQuantity(cardId, 1, boardId);
  };
  const handleBoardRowSecondaryAction = (
    cardId: string,
    boardId = boards.activeBoardId.value,
  ): void => {
    if (!constraints.boardRowSecondaryActionDisabled(cardId, boardId)) {
      changeQuantity(cardId, -1, boardId);
    }
  };
  const moveEntryToBoard = (
    cardId: string,
    destinationBoardId: string,
    sourceBoardId = boards.activeBoardId.value,
  ): boolean =>
    constraints.getMoveEntryToBoardValidationError(cardId, destinationBoardId, sourceBoardId) ===
      null && boards.moveEntryToBoardUnchecked(cardId, destinationBoardId, sourceBoardId);

  return {
    form,
    isHeroStep,
    isDetailsStep,
    isCardsStep,
    activeBoardId: boards.activeBoardId,
    lastBoardEntryChange: boards.lastBoardEntryChange,
    totalMainboardCards: metrics.totalMainboardCards,
    totalSideboardCards: metrics.totalSideboardCards,
    overallTotalCards: metrics.overallTotalCards,
    overallUniqueCards: metrics.overallUniqueCards,
    allCardIds: metrics.allCardIds,
    selectedHero,
    detailedMainboardEntries: metrics.detailedMainboardEntries,
    detailedActiveBoardEntries: metrics.detailedActiveBoardEntries,
    totalMainboardManaTypeCards: metrics.totalMainboardManaTypeCards,
    hasFreeMulliganManaRatio: metrics.hasFreeMulliganManaRatio,
    activeSideboard: boards.activeSideboard,
    sideboardTabs: boards.sideboardTabs,
    deckTypeCounts: metrics.deckTypeCounts,
    headerDeckTypeCounts: metrics.headerDeckTypeCounts,
    remainingDeckTypeCount: metrics.remainingDeckTypeCount,
    setupMessages: metrics.setupMessages,
    validationMessages: metrics.validationMessages,
    warningMessages: metrics.warningMessages,
    blockingMessages: metrics.blockingMessages,
    isDeckValid: metrics.isDeckValid,
    deckStatusLabel: metrics.deckStatusLabel,
    setDeckName,
    setDeckDescription,
    setDeckLongDescription,
    setDeckDifficulty,
    setDeckVisibility,
    setDeckTagIds,
    setSuggestedTypeLabels,
    selectBoard: boards.selectBoard,
    addSideboard: boards.addSideboard,
    renameSideboard: boards.renameSideboard,
    removeSideboard: boards.removeSideboard,
    hydrateFromDeck,
    hydrateFromLocalDraft,
    resetLocalDraft,
    buildPayload,
    getEntryQuantity: boards.getEntryQuantity,
    getCardQuantityLimit: constraints.getCardQuantityLimit,
    getCardQuantityLimitMessage: constraints.getCardQuantityLimitMessage,
    changeQuantity,
    setQuantity,
    reorderEntries: boards.reorderEntries,
    moveEntryWithinBoard: boards.moveEntryWithinBoard,
    moveEntryToIndex: boards.moveEntryToIndex,
    removeEntry: boards.removeEntry,
    galleryActionLabel: constraints.galleryActionLabel,
    galleryActionDisabled: constraints.galleryActionDisabled,
    galleryRemoveActionDisabled: constraints.galleryRemoveActionDisabled,
    boardRowActionDisabled: constraints.boardRowActionDisabled,
    boardRowSecondaryActionDisabled: constraints.boardRowSecondaryActionDisabled,
    getMoveEntryToBoardValidationError: constraints.getMoveEntryToBoardValidationError,
    getBoardMoveDestinations: constraints.getBoardMoveDestinations,
    handleGalleryAction,
    handleGalleryRemoveAction,
    handleBoardRowAction,
    handleBoardRowSecondaryAction,
    moveEntryToBoard,
  };
};

export type DeckEditorDraftController = ReturnType<typeof useDeckEditorDraft>;
