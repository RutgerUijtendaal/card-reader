import { computed, getCurrentScope, onScopeDispose, ref } from 'vue';
import type {
  DeckBoardEntryChange,
  DeckBoardEntryChangeKind,
  DeckForm,
  DeckFormEntry,
} from '@/features/decks/composables/deckEditorDraftTypes';

export const MAINBOARD_ID = 'mainboard';
const BOARD_ENTRY_POP_DURATION_MS = 320;

type PendingRemovedDeckEntry = DeckFormEntry & {
  boardId: string;
  index: number;
};

const buildLocalSideboardId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `sideboard-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
};

export const useDeckEditorBoards = (form: DeckForm) => {
  const activeBoardId = ref<string>(MAINBOARD_ID);
  const lastBoardEntryChange = ref<DeckBoardEntryChange | null>(null);
  const pendingRemovedEntries = ref<PendingRemovedDeckEntry[]>([]);
  const pendingRemovalTimers = new Map<string, number>();
  let boardEntryChangeSequence = 0;

  const boardEntryKey = (cardId: string, boardId: string): string => `${boardId}:${cardId}`;

  const clearPendingRemovedEntry = (cardId: string, boardId: string): void => {
    const key = boardEntryKey(cardId, boardId);
    const timer = pendingRemovalTimers.get(key);
    if (timer !== undefined) {
      window.clearTimeout(timer);
      pendingRemovalTimers.delete(key);
    }
    pendingRemovedEntries.value = pendingRemovedEntries.value.filter(
      (entry) => entry.card_id !== cardId || entry.boardId !== boardId,
    );
  };

  const schedulePendingRemovedEntry = (entry: DeckFormEntry, boardId: string, index: number): void => {
    clearPendingRemovedEntry(entry.card_id, boardId);
    pendingRemovedEntries.value = [...pendingRemovedEntries.value, { ...entry, boardId, index }];
    const timer = window.setTimeout(() => {
      pendingRemovedEntries.value = pendingRemovedEntries.value.filter(
        (pendingEntry) => pendingEntry.card_id !== entry.card_id || pendingEntry.boardId !== boardId,
      );
      pendingRemovalTimers.delete(boardEntryKey(entry.card_id, boardId));
    }, BOARD_ENTRY_POP_DURATION_MS);
    pendingRemovalTimers.set(boardEntryKey(entry.card_id, boardId), timer);
  };

  const clearPendingRemovedEntries = (): void => {
    for (const timer of pendingRemovalTimers.values()) window.clearTimeout(timer);
    pendingRemovalTimers.clear();
    pendingRemovedEntries.value = [];
  };

  const notifyBoardEntryChange = (
    cardId: string,
    boardId: string,
    kind: DeckBoardEntryChangeKind,
  ): void => {
    boardEntryChangeSequence += 1;
    lastBoardEntryChange.value = { cardId, boardId, kind, sequence: boardEntryChangeSequence };
  };

  if (getCurrentScope()) onScopeDispose(clearPendingRemovedEntries);

  const activeSideboard = computed(
    () => form.sideboards.find((sideboard) => sideboard.id === activeBoardId.value) ?? null,
  );
  const activeBoardEntries = computed(() =>
    activeBoardId.value === MAINBOARD_ID ? form.entries : activeSideboard.value?.entries ?? [],
  );
  const visibleActiveBoardEntries = computed<DeckFormEntry[]>(() => {
    const entries = [...activeBoardEntries.value];
    const pendingEntries = pendingRemovedEntries.value
      .filter((entry) => entry.boardId === activeBoardId.value)
      .sort((left, right) => left.index - right.index);
    for (const { card_id, quantity, index } of pendingEntries) {
      entries.splice(Math.min(index, entries.length), 0, { card_id, quantity });
    }
    return entries;
  });
  const sideboardTabs = computed(() =>
    form.sideboards.map((sideboard) => ({
      id: sideboard.id,
      name: sideboard.name.trim() || 'Untitled Sideboard',
      totalCards: sideboard.entries.reduce((sum, entry) => sum + entry.quantity, 0),
      uniqueCards: sideboard.entries.length,
    })),
  );

  const selectBoard = (boardId: string): void => {
    activeBoardId.value = boardId;
  };
  const addSideboard = (): void => {
    const id = buildLocalSideboardId();
    form.sideboards = [
      ...form.sideboards,
      { id, name: `Sideboard ${form.sideboards.length + 1}`, entries: [] },
    ];
    activeBoardId.value = id;
  };
  const renameSideboard = (sideboardId: string, name: string): void => {
    form.sideboards = form.sideboards.map((sideboard) =>
      sideboard.id === sideboardId ? { ...sideboard, name } : sideboard,
    );
  };
  const removeSideboard = (sideboardId: string): void => {
    form.sideboards = form.sideboards.filter((sideboard) => sideboard.id !== sideboardId);
    pendingRemovedEntries.value
      .filter((entry) => entry.boardId === sideboardId)
      .forEach((entry) => clearPendingRemovedEntry(entry.card_id, sideboardId));
    if (activeBoardId.value === sideboardId) activeBoardId.value = MAINBOARD_ID;
  };

  const getBoardEntries = (boardId: string): DeckFormEntry[] =>
    boardId === MAINBOARD_ID
      ? form.entries
      : form.sideboards.find((sideboard) => sideboard.id === boardId)?.entries ?? [];
  const getEntryQuantity = (cardId: string, boardId = activeBoardId.value): number =>
    getBoardEntries(boardId).find((entry) => entry.card_id === cardId)?.quantity ?? 0;
  const getBoardLabel = (boardId: string): string =>
    boardId === MAINBOARD_ID
      ? 'Mainboard'
      : form.sideboards.find((sideboard) => sideboard.id === boardId)?.name.trim() ||
        'Untitled Sideboard';
  const updateBoardEntries = (boardId: string, entries: DeckFormEntry[]): void => {
    if (boardId === MAINBOARD_ID) form.entries = entries;
    else {
      form.sideboards = form.sideboards.map((sideboard) =>
        sideboard.id === boardId ? { ...sideboard, entries } : sideboard,
      );
    }
  };

  const reorderEntries = (boardId: string, movedCardId: string, targetCardId: string): void => {
    if (movedCardId === targetCardId) return;
    const entries = getBoardEntries(boardId);
    const movedIndex = entries.findIndex((entry) => entry.card_id === movedCardId);
    if (movedIndex < 0) return;
    const nextEntries = [...entries];
    const [movedEntry] = nextEntries.splice(movedIndex, 1);
    const targetIndex = nextEntries.findIndex((entry) => entry.card_id === targetCardId);
    if (!movedEntry || targetIndex < 0) return;
    nextEntries.splice(targetIndex, 0, movedEntry);
    updateBoardEntries(boardId, nextEntries);
  };
  const moveEntryWithinBoard = (
    cardId: string,
    direction: -1 | 1,
    boardId = activeBoardId.value,
  ): void => {
    const entries = getBoardEntries(boardId);
    const currentIndex = entries.findIndex((entry) => entry.card_id === cardId);
    const nextIndex = currentIndex + direction;
    if (currentIndex < 0 || nextIndex < 0 || nextIndex >= entries.length) return;
    const nextEntries = [...entries];
    const [movedEntry] = nextEntries.splice(currentIndex, 1);
    if (!movedEntry) return;
    nextEntries.splice(nextIndex, 0, movedEntry);
    updateBoardEntries(boardId, nextEntries);
  };
  const moveEntryToIndex = (boardId: string, movedCardId: string, targetIndex: number): void => {
    const entries = getBoardEntries(boardId);
    const movedIndex = entries.findIndex((entry) => entry.card_id === movedCardId);
    if (movedIndex < 0) return;
    const nextEntries = [...entries];
    const [movedEntry] = nextEntries.splice(movedIndex, 1);
    if (!movedEntry) return;
    nextEntries.splice(Math.max(0, Math.min(targetIndex, nextEntries.length)), 0, movedEntry);
    updateBoardEntries(boardId, nextEntries);
  };
  const removeEntry = (cardId: string, boardId = activeBoardId.value): void => {
    const entries = getBoardEntries(boardId);
    const index = entries.findIndex((entry) => entry.card_id === cardId);
    const currentEntry = index >= 0 ? entries[index] : null;
    if (!currentEntry || currentEntry.quantity <= 0) return;
    updateBoardEntries(boardId, entries.filter((entry) => entry.card_id !== cardId));
    schedulePendingRemovedEntry(currentEntry, boardId, index);
    notifyBoardEntryChange(cardId, boardId, 'remove');
  };
  const moveEntryToBoardUnchecked = (
    cardId: string,
    destinationBoardId: string,
    sourceBoardId = activeBoardId.value,
  ): boolean => {
    const sourceEntries = getBoardEntries(sourceBoardId);
    const sourceEntry = sourceEntries.find((entry) => entry.card_id === cardId);
    if (!sourceEntry) return false;
    const destinationEntries = getBoardEntries(destinationBoardId);
    const destinationEntry = destinationEntries.find((entry) => entry.card_id === cardId);
    updateBoardEntries(
      sourceBoardId,
      sourceEntries.flatMap((entry) =>
        entry.card_id !== cardId
          ? [entry]
          : entry.quantity <= 1
            ? []
            : [{ ...entry, quantity: entry.quantity - 1 }],
      ),
    );
    updateBoardEntries(
      destinationBoardId,
      destinationEntry
        ? destinationEntries.map((entry) =>
            entry.card_id === cardId ? { ...entry, quantity: entry.quantity + 1 } : entry,
          )
        : [...destinationEntries, { card_id: cardId, quantity: 1 }],
    );
    return true;
  };

  return {
    activeBoardId,
    lastBoardEntryChange,
    activeSideboard,
    activeBoardEntries,
    visibleActiveBoardEntries,
    sideboardTabs,
    selectBoard,
    addSideboard,
    renameSideboard,
    removeSideboard,
    getBoardEntries,
    getEntryQuantity,
    getBoardLabel,
    updateBoardEntries,
    reorderEntries,
    moveEntryWithinBoard,
    moveEntryToIndex,
    removeEntry,
    moveEntryToBoardUnchecked,
    clearPendingRemovedEntry,
    clearPendingRemovedEntries,
    notifyBoardEntryChange,
  };
};
