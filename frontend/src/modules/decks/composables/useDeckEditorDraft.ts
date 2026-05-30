import { computed, reactive, ref, type Ref } from 'vue';
import type { CardListItem } from '@/modules/card-detail/types';
import {
  MAX_DECK_COPIES,
  MAX_MAINBOARD_CARD_COUNT,
  MAX_SIDEBOARD_ENTRY_QUANTITY,
} from '@/modules/decks/constants';
import {
  getDeckConstraintMessages,
  getDeckEntryQuantityLimit,
  getDeckQuantityViolationMessage,
  getDeckWarningMessages,
  resolveDeckBuildingRules,
  type DeckBuildingRules,
  type DeckConstraintContext,
} from '@/modules/decks/deckConstraints';
import { fallbackDeckBuildingRules } from '@/modules/decks/deckRules';
import type { DeckCardSummary, DeckMetadataOption, DeckRecord, DeckUpsertRequest, DeckVisibility } from '@/modules/decks/types';

export type DeckFormEntry = {
  card_id: string;
  quantity: number;
};

export type DeckFormSideboard = {
  id: string;
  name: string;
  entries: DeckFormEntry[];
};

export type DeckForm = {
  name: string;
  description: string;
  visibility: DeckVisibility;
  hero_card_id: string;
  entries: DeckFormEntry[];
  sideboards: DeckFormSideboard[];
};

export type BuilderStep = 'setup' | 'build';
export type DeckBoardMoveDestination = {
  boardId: string;
  label: string;
  description?: string;
  disabled: boolean;
};

type UseDeckEditorDraftOptions = {
  builderStep: Ref<BuilderStep>;
  cardLookup: Ref<Record<string, DeckCardSummary>>;
  deckBuildingRules?: Ref<DeckBuildingRules>;
  rememberCards: (cards: CardListItem[]) => void;
};

const MAINBOARD_ID = 'mainboard';

const buildLocalSideboardId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `sideboard-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
};

export const useDeckEditorDraft = ({
  builderStep,
  cardLookup,
  deckBuildingRules: baseDeckBuildingRules,
  rememberCards,
}: UseDeckEditorDraftOptions) => {
  const effectiveBaseDeckBuildingRules = baseDeckBuildingRules ?? ref(fallbackDeckBuildingRules());
  const form = reactive<DeckForm>({
    name: '',
    description: '',
    visibility: 'private',
    hero_card_id: '',
    entries: [],
    sideboards: [],
  });
  const activeBoardId = ref<string>(MAINBOARD_ID);

  const isSetupStep = computed(() => builderStep.value === 'setup');
  const selectedHero = computed(() => (form.hero_card_id ? cardLookup.value[form.hero_card_id] ?? null : null));
  const totalMainboardCards = computed(() => form.entries.reduce((sum, entry) => sum + entry.quantity, 0));
  const totalSideboardCards = computed(() =>
    form.sideboards.reduce((sum, sideboard) => sum + sideboard.entries.reduce((boardSum, entry) => boardSum + entry.quantity, 0), 0),
  );
  const overallTotalCards = computed(() => totalMainboardCards.value + totalSideboardCards.value);
  const overallUniqueCards = computed(() => {
    const uniqueCardIds = new Set(form.entries.map((entry) => entry.card_id));
    for (const sideboard of form.sideboards) {
      for (const entry of sideboard.entries) {
        uniqueCardIds.add(entry.card_id);
      }
    }
    return uniqueCardIds.size;
  });
  const allCardIds = computed(() => {
    const uniqueCardIds = new Set<string>();
    for (const entry of form.entries) {
      uniqueCardIds.add(entry.card_id);
    }
    for (const sideboard of form.sideboards) {
      for (const entry of sideboard.entries) {
        uniqueCardIds.add(entry.card_id);
      }
    }
    return [...uniqueCardIds].sort((left, right) => left.localeCompare(right));
  });
  const sideboardTabs = computed(() =>
    form.sideboards.map((sideboard) => ({
      id: sideboard.id,
      name: sideboard.name.trim() || 'Untitled Sideboard',
      totalCards: sideboard.entries.reduce((sum, entry) => sum + entry.quantity, 0),
      uniqueCards: sideboard.entries.length,
    })),
  );
  const activeSideboard = computed(() => form.sideboards.find((sideboard) => sideboard.id === activeBoardId.value) ?? null);
  const activeBoardEntries = computed(() => (activeBoardId.value === MAINBOARD_ID ? form.entries : activeSideboard.value?.entries ?? []));
  const baseConstraintContext = computed(() => ({
    mainboardId: MAINBOARD_ID,
    heroCard: selectedHero.value,
    cardLookup: cardLookup.value,
    baseRules: effectiveBaseDeckBuildingRules.value,
    mainboardEntries: form.entries,
    sideboards: form.sideboards,
  }));
  const deckBuildingRules = computed(() => resolveDeckBuildingRules(baseConstraintContext.value));
  const mainboardMaxCards = computed(() => deckBuildingRules.value.mainboard_card_count.max ?? MAX_MAINBOARD_CARD_COUNT);

  const mapDetailedEntries = (entries: DeckFormEntry[]) =>
    entries
      .map((entry) => ({
        card: cardLookup.value[entry.card_id],
        quantity: entry.quantity,
      }))
      .filter((entry): entry is { card: DeckCardSummary; quantity: number } => Boolean(entry.card));

  const detailedMainboardEntries = computed(() => mapDetailedEntries(form.entries));
  const detailedActiveBoardEntries = computed(() => mapDetailedEntries(activeBoardEntries.value));
  const totalMainboardManaTypeCards = computed(() =>
    detailedMainboardEntries.value.reduce(
      (sum, entry) => sum + (entry.card.types.some((type) => type.key.toLowerCase() === 'mana') ? entry.quantity : 0),
      0,
    ),
  );
  const hasFreeMulliganManaRatio = computed(() =>
    totalMainboardCards.value > 0
    && totalMainboardManaTypeCards.value / totalMainboardCards.value >= 0.25,
  );

  const deckTypeCounts = computed(() => {
    const counts = new Map<string, { type: DeckMetadataOption; count: number }>();

    const addTypes = (types: DeckMetadataOption[], quantity: number): void => {
      for (const type of types) {
        const existing = counts.get(type.id);
        if (existing) {
          existing.count += quantity;
          continue;
        }
        counts.set(type.id, { type, count: quantity });
      }
    };

    if (selectedHero.value) {
      addTypes(selectedHero.value.types, 1);
    }

    for (const entry of [...detailedMainboardEntries.value, ...form.sideboards.flatMap((sideboard) => mapDetailedEntries(sideboard.entries))]) {
      addTypes(entry.card.types, entry.quantity);
    }

    return [...counts.values()].sort((left, right) => {
      if (right.count !== left.count) {
        return right.count - left.count;
      }
      return left.type.label.localeCompare(right.type.label);
    });
  });

  const headerDeckTypeCounts = computed(() => deckTypeCounts.value.slice(0, 4));
  const remainingDeckTypeCount = computed(() => Math.max(deckTypeCounts.value.length - headerDeckTypeCounts.value.length, 0));

  const setupMessages = computed(() => {
    const messages: string[] = [];
    if (!form.name.trim()) messages.push('Deck name is required.');
    if (!form.hero_card_id) messages.push('A hero card is required.');
    return messages;
  });

  const validationMessages = computed(() => {
    const messages = [...setupMessages.value];
    for (const sideboard of form.sideboards) {
      if (!sideboard.name.trim()) {
        messages.push('Each sideboard needs a name.');
        break;
      }
    }
    messages.push(...getDeckConstraintMessages(baseConstraintContext.value));
    return messages;
  });
  const warningMessages = computed(() => getDeckWarningMessages(baseConstraintContext.value));

  const isDeckValid = computed(() => validationMessages.value.length === 0);
  const deckStatusLabel = computed(() => (isDeckValid.value ? 'Ready' : 'In Progress'));

  const setDeckName = (value: string): void => {
    form.name = value;
  };

  const setDeckDescription = (value: string): void => {
    form.description = value;
  };

  const setDeckVisibility = (value: DeckVisibility): void => {
    form.visibility = value;
  };

  const selectBoard = (boardId: string): void => {
    activeBoardId.value = boardId;
  };

  const addSideboard = (): void => {
    const nextId = buildLocalSideboardId();
    form.sideboards = [
      ...form.sideboards,
      {
        id: nextId,
        name: `Sideboard ${form.sideboards.length + 1}`,
        entries: [],
      },
    ];
    activeBoardId.value = nextId;
  };

  const renameSideboard = (sideboardId: string, name: string): void => {
    form.sideboards = form.sideboards.map((sideboard) => (sideboard.id === sideboardId ? { ...sideboard, name } : sideboard));
  };

  const removeSideboard = (sideboardId: string): void => {
    form.sideboards = form.sideboards.filter((sideboard) => sideboard.id !== sideboardId);
    if (activeBoardId.value === sideboardId) {
      activeBoardId.value = MAINBOARD_ID;
    }
  };

  const hydrateFromDeck = (deck: DeckRecord): void => {
    form.name = deck.name;
    form.description = deck.description ?? '';
    form.visibility = deck.visibility;
    form.hero_card_id = deck.hero_card.id;
    form.entries = deck.mainboard.entries.map((entry) => ({
      card_id: entry.card.id,
      quantity: entry.quantity,
    }));
    form.sideboards = deck.sideboards.map((sideboard) => ({
      id: sideboard.id,
      name: sideboard.name,
      entries: sideboard.entries.map((entry) => ({
        card_id: entry.card.id,
        quantity: entry.quantity,
      })),
    }));
    activeBoardId.value = MAINBOARD_ID;

    const nextLookup = { ...cardLookup.value, [deck.hero_card.id]: deck.hero_card };
    for (const entry of deck.mainboard.entries) {
      nextLookup[entry.card.id] = entry.card;
    }
    for (const sideboard of deck.sideboards) {
      for (const entry of sideboard.entries) {
        nextLookup[entry.card.id] = entry.card;
      }
    }
    cardLookup.value = nextLookup;
  };

  const buildPayload = (): DeckUpsertRequest => ({
    name: form.name.trim(),
    description: form.description.trim() || null,
    visibility: form.visibility,
    hero_card_id: form.hero_card_id,
    entries: form.entries.map((entry) => ({
      card_id: entry.card_id,
      quantity: entry.quantity,
    })),
    sideboards: form.sideboards.map((sideboard) => ({
      name: sideboard.name.trim(),
      entries: sideboard.entries.map((entry) => ({
        card_id: entry.card_id,
        quantity: entry.quantity,
      })),
    })),
  });

  const getBoardEntries = (boardId: string): DeckFormEntry[] => {
    if (boardId === MAINBOARD_ID) {
      return form.entries;
    }
    return form.sideboards.find((sideboard) => sideboard.id === boardId)?.entries ?? [];
  };

  const getEntryQuantity = (cardId: string, boardId = activeBoardId.value): number =>
    getBoardEntries(boardId).find((entry) => entry.card_id === cardId)?.quantity ?? 0;

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
      entries.flatMap((entry) => {
        if (entry.card_id !== cardId) {
          return [entry];
        }
        if (entry.quantity <= 1) {
          return [];
        }
        return [{ ...entry, quantity: entry.quantity - 1 }];
      });

    return {
      mainboardId: MAINBOARD_ID,
      boardId: destinationBoardId,
      heroCard: selectedHero.value,
      cardLookup: cardLookup.value,
      baseRules: effectiveBaseDeckBuildingRules.value,
      mainboardEntries: sourceBoardId === MAINBOARD_ID ? removeMovedCopy(form.entries) : form.entries,
      sideboards: form.sideboards.map((sideboard) => ({
        ...sideboard,
        entries: sourceBoardId === sideboard.id ? removeMovedCopy(sideboard.entries) : sideboard.entries,
      })),
    };
  };

  const getCardQuantityLimit = (cardId: string, boardId = activeBoardId.value): number => {
    const card = cardLookup.value[cardId];
    if (!card) {
      return boardId === MAINBOARD_ID
        ? (deckBuildingRules.value.mainboard_copy_limit.max ?? MAX_DECK_COPIES)
        : (deckBuildingRules.value.sideboard_entry_quantity.max ?? MAX_SIDEBOARD_ENTRY_QUANTITY);
    }
    return getDeckEntryQuantityLimit(card, getConstraintContext(boardId)).max;
  };

  const getCardQuantityLimitMessage = (cardId: string, boardId = activeBoardId.value): string => {
    const card = cardLookup.value[cardId];
    if (!card) {
      const max = boardId === MAINBOARD_ID
        ? (deckBuildingRules.value.mainboard_copy_limit.max ?? MAX_DECK_COPIES)
        : (deckBuildingRules.value.sideboard_entry_quantity.max ?? MAX_SIDEBOARD_ENTRY_QUANTITY);
      return boardId === MAINBOARD_ID
        ? `Mainboard copy limit is ${max}.`
        : `Sideboard copy limit is ${max}.`;
    }
    return getDeckEntryQuantityLimit(card, getConstraintContext(boardId)).message;
  };

  const getBoardLabel = (boardId: string): string => {
    if (boardId === MAINBOARD_ID) {
      return 'Mainboard';
    }
    return form.sideboards.find((sideboard) => sideboard.id === boardId)?.name.trim() || 'Untitled Sideboard';
  };

  const updateBoardEntries = (boardId: string, entries: DeckFormEntry[]): void => {
    if (boardId === MAINBOARD_ID) {
      form.entries = entries;
      return;
    }
    form.sideboards = form.sideboards.map((sideboard) => (sideboard.id === boardId ? { ...sideboard, entries } : sideboard));
  };

  const addEntry = (card: CardListItem): void => {
    rememberCards([card]);
    const boardId = activeBoardId.value;
    const currentQuantity = getEntryQuantity(card.id, boardId);
    const quantityLimit = getDeckEntryQuantityLimit(card, getConstraintContext(boardId)).max;
    if (boardId === MAINBOARD_ID) {
      if (currentQuantity >= quantityLimit || totalMainboardCards.value >= mainboardMaxCards.value) {
        return;
      }
      if (currentQuantity === 0) {
        form.entries = [...form.entries, { card_id: card.id, quantity: 1 }];
        return;
      }
      form.entries = form.entries.map((entry) =>
        entry.card_id === card.id ? { ...entry, quantity: Math.min(quantityLimit, entry.quantity + 1) } : entry,
      );
      return;
    }

    const boardEntries = getBoardEntries(boardId);
    if (currentQuantity >= quantityLimit) {
      return;
    }
    if (currentQuantity === 0) {
      updateBoardEntries(boardId, [...boardEntries, { card_id: card.id, quantity: 1 }]);
      return;
    }
    updateBoardEntries(
      boardId,
      boardEntries.map((entry) =>
        entry.card_id === card.id
          ? { ...entry, quantity: Math.min(quantityLimit, entry.quantity + 1) }
          : entry,
      ),
    );
  };

  const removeEntry = (cardId: string, boardId = activeBoardId.value): void => {
    updateBoardEntries(
      boardId,
      getBoardEntries(boardId).filter((entry) => entry.card_id !== cardId),
    );
  };

  const changeQuantity = (cardId: string, delta: number, boardId = activeBoardId.value): void => {
    const boardEntries = getBoardEntries(boardId);
    updateBoardEntries(
      boardId,
      boardEntries.map((entry) => {
        if (entry.card_id !== cardId) {
          return entry;
        }
        const quantityLimit = getCardQuantityLimit(cardId, boardId);
        const nextQuantity =
          Math.max(1, Math.min(quantityLimit, entry.quantity + delta));
        return { ...entry, quantity: nextQuantity };
      }),
    );
  };

  const setQuantity = (cardId: string, rawValue: string, boardId = activeBoardId.value): void => {
    const parsed = Number.parseInt(rawValue, 10);
    const quantityLimit = getCardQuantityLimit(cardId, boardId);
    const quantity = Number.isNaN(parsed)
      ? 1
      : Math.max(1, Math.min(quantityLimit, parsed));
    updateBoardEntries(
      boardId,
      getBoardEntries(boardId).map((entry) => (entry.card_id === cardId ? { ...entry, quantity } : entry)),
    );
  };

  const galleryActionLabel = (card: CardListItem): string => {
    if (isSetupStep.value) {
      return form.hero_card_id === card.id ? 'Selected Hero' : 'Use As Hero';
    }

    const boardId = activeBoardId.value;
    const quantity = getEntryQuantity(card.id, boardId);
    const quantityLimit = getDeckEntryQuantityLimit(card, getConstraintContext(boardId)).max;
    if (boardId === MAINBOARD_ID) {
      if (quantity === 0 && totalMainboardCards.value >= mainboardMaxCards.value) return 'Mainboard Full';
      if (quantity === 0) return 'Add To Mainboard';
      if (quantity >= quantityLimit) return quantityLimit === 1 ? 'At Legendary Limit' : 'At Copy Limit';
      if (totalMainboardCards.value >= mainboardMaxCards.value) return `At Mainboard Limit (${quantity})`;
      return `Add Copy (${quantity}/${quantityLimit})`;
    }
    if (quantity === 0) return 'Add To Sideboard';
    if (quantity >= quantityLimit) return quantityLimit === 1 ? 'At Legendary Limit' : 'At Sideboard Limit';
    return `Add Copy (${quantity})`;
  };

  const galleryActionDisabled = (card: CardListItem): boolean => {
    if (isSetupStep.value) {
      return form.hero_card_id === card.id;
    }

    const boardId = activeBoardId.value;
    const quantity = getEntryQuantity(card.id, boardId);
    if (boardId === MAINBOARD_ID) {
      return quantity >= getDeckEntryQuantityLimit(card, getConstraintContext(boardId)).max
        || (quantity === 0 && totalMainboardCards.value >= mainboardMaxCards.value);
    }
    return quantity >= getDeckEntryQuantityLimit(card, getConstraintContext(boardId)).max;
  };

  const galleryRemoveActionDisabled = (cardId: string, boardId = activeBoardId.value): boolean => {
    if (isSetupStep.value) {
      return true;
    }
    return getEntryQuantity(cardId, boardId) <= 0;
  };

  const boardRowActionDisabled = (cardId: string, boardId = activeBoardId.value): boolean => {
    if (isSetupStep.value) {
      return true;
    }

    const quantity = getEntryQuantity(cardId, boardId);
    if (quantity <= 0) {
      return true;
    }
    if (boardId === MAINBOARD_ID) {
      return quantity >= getCardQuantityLimit(cardId, boardId) || totalMainboardCards.value >= mainboardMaxCards.value;
    }
    return quantity >= getCardQuantityLimit(cardId, boardId);
  };

  const boardRowSecondaryActionDisabled = (cardId: string, boardId = activeBoardId.value): boolean => {
    if (isSetupStep.value) {
      return true;
    }
    return getEntryQuantity(cardId, boardId) <= 1;
  };

  const getMoveEntryToBoardValidationError = (
    cardId: string,
    destinationBoardId: string,
    sourceBoardId = activeBoardId.value,
  ): string | null => {
    if (isSetupStep.value) {
      return 'Cards cannot be moved during setup.';
    }
    if (destinationBoardId === sourceBoardId) {
      return 'Card is already on that board.';
    }

    const sourceQuantity = getEntryQuantity(cardId, sourceBoardId);
    if (sourceQuantity <= 0) {
      return 'Card is not on the current board.';
    }

    const destinationQuantity = getEntryQuantity(cardId, destinationBoardId);
    const moveQuantity = 1;
    const nextDestinationQuantity = destinationQuantity + moveQuantity;
    const card = cardLookup.value[cardId];
    if (card) {
      const constraintMessage = getDeckQuantityViolationMessage(
        card,
        nextDestinationQuantity,
        getMoveConstraintContext(cardId, sourceBoardId, destinationBoardId),
      );
      if (constraintMessage !== null) {
        return constraintMessage;
      }
    }

    if (destinationBoardId === MAINBOARD_ID) {
      if (totalMainboardCards.value + moveQuantity > mainboardMaxCards.value) {
        return `Mainboard cannot exceed ${mainboardMaxCards.value} cards.`;
      }
      return null;
    }

    return null;
  };

  const getBoardMoveDestinations = (cardId: string, sourceBoardId = activeBoardId.value): DeckBoardMoveDestination[] => {
    if (isSetupStep.value) {
      return [];
    }

    const destinations: DeckBoardMoveDestination[] = [];
    if (sourceBoardId !== MAINBOARD_ID) {
      const error = getMoveEntryToBoardValidationError(cardId, MAINBOARD_ID, sourceBoardId);
      destinations.push({
        boardId: MAINBOARD_ID,
        label: getBoardLabel(MAINBOARD_ID),
        description: error ?? undefined,
        disabled: error !== null,
      });
    }

    for (const sideboard of form.sideboards) {
      if (sideboard.id === sourceBoardId) {
        continue;
      }
      const error = getMoveEntryToBoardValidationError(cardId, sideboard.id, sourceBoardId);
      destinations.push({
        boardId: sideboard.id,
        label: getBoardLabel(sideboard.id),
        description: error ?? undefined,
        disabled: error !== null,
      });
    }

    return destinations;
  };

  const handleGalleryAction = (card: CardListItem): void => {
    if (isSetupStep.value) {
      rememberCards([card]);
      form.hero_card_id = card.id;
      return;
    }
    addEntry(card);
  };

  const handleGalleryRemoveAction = (cardId: string, boardId = activeBoardId.value): void => {
    if (galleryRemoveActionDisabled(cardId, boardId)) {
      return;
    }

    const quantity = getEntryQuantity(cardId, boardId);
    if (quantity <= 1) {
      removeEntry(cardId, boardId);
      return;
    }

    changeQuantity(cardId, -1, boardId);
  };

  const handleBoardRowAction = (cardId: string, boardId = activeBoardId.value): void => {
    if (boardRowActionDisabled(cardId, boardId)) {
      return;
    }
    changeQuantity(cardId, 1, boardId);
  };

  const handleBoardRowSecondaryAction = (cardId: string, boardId = activeBoardId.value): void => {
    if (boardRowSecondaryActionDisabled(cardId, boardId)) {
      return;
    }
    changeQuantity(cardId, -1, boardId);
  };

  const moveEntryToBoard = (cardId: string, destinationBoardId: string, sourceBoardId = activeBoardId.value): boolean => {
    const error = getMoveEntryToBoardValidationError(cardId, destinationBoardId, sourceBoardId);
    if (error !== null) {
      return false;
    }

    const sourceEntries = getBoardEntries(sourceBoardId);
    const sourceEntry = sourceEntries.find((entry) => entry.card_id === cardId);
    if (!sourceEntry) {
      return false;
    }
    const moveQuantity = 1;

    const destinationEntries = getBoardEntries(destinationBoardId);
    const destinationEntry = destinationEntries.find((entry) => entry.card_id === cardId);

    updateBoardEntries(
      sourceBoardId,
      sourceEntries.flatMap((entry) => {
        if (entry.card_id !== cardId) {
          return [entry];
        }
        if (entry.quantity <= moveQuantity) {
          return [];
        }
        return [{ ...entry, quantity: entry.quantity - moveQuantity }];
      }),
    );
    updateBoardEntries(
      destinationBoardId,
      destinationEntry
        ? destinationEntries.map((entry) =>
            entry.card_id === cardId
              ? { ...entry, quantity: entry.quantity + moveQuantity }
              : entry,
          )
        : [...destinationEntries, { card_id: cardId, quantity: moveQuantity }],
    );

    return true;
  };

  return {
    form,
    isSetupStep,
    activeBoardId,
    totalMainboardCards,
    totalSideboardCards,
    overallTotalCards,
    overallUniqueCards,
    allCardIds,
    selectedHero,
    detailedMainboardEntries,
    detailedActiveBoardEntries,
    totalMainboardManaTypeCards,
    hasFreeMulliganManaRatio,
    activeSideboard,
    sideboardTabs,
    deckTypeCounts,
    headerDeckTypeCounts,
    remainingDeckTypeCount,
    setupMessages,
    validationMessages,
    warningMessages,
    isDeckValid,
    deckStatusLabel,
    setDeckName,
    setDeckDescription,
    setDeckVisibility,
    selectBoard,
    addSideboard,
    renameSideboard,
    removeSideboard,
    hydrateFromDeck,
    buildPayload,
    getEntryQuantity,
    getCardQuantityLimit,
    getCardQuantityLimitMessage,
    changeQuantity,
    setQuantity,
    removeEntry,
    galleryActionLabel,
    galleryActionDisabled,
    galleryRemoveActionDisabled,
    boardRowActionDisabled,
    boardRowSecondaryActionDisabled,
    getMoveEntryToBoardValidationError,
    getBoardMoveDestinations,
    handleGalleryAction,
    handleGalleryRemoveAction,
    handleBoardRowAction,
    handleBoardRowSecondaryAction,
    moveEntryToBoard,
  };
};

export type DeckEditorDraftController = ReturnType<typeof useDeckEditorDraft>;
