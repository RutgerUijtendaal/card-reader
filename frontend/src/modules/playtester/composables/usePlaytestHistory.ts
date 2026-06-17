import { ref, type Ref } from 'vue';
import type { PlaytestState } from '@/modules/playtester/types';

type ApplyPlaytestStateOptions = {
  recordHistory?: boolean;
};

type UsePlaytestHistoryOptions = {
  playtest: Ref<PlaytestState | null>;
  clearTransientUi: () => void;
  pruneState: (nextState: PlaytestState) => void;
  clearSelection: () => void;
};

const PLAYTEST_HISTORY_LIMIT = 100;

export const usePlaytestHistory = ({
  playtest,
  clearTransientUi,
  pruneState,
  clearSelection,
}: UsePlaytestHistoryOptions) => {
  const undoStack = ref<PlaytestState[]>([]);
  const redoStack = ref<PlaytestState[]>([]);

  const pushUndoState = (state: PlaytestState): void => {
    undoStack.value = [...undoStack.value, state].slice(-PLAYTEST_HISTORY_LIMIT);
  };

  const pushRedoState = (state: PlaytestState): void => {
    redoStack.value = [...redoStack.value, state].slice(-PLAYTEST_HISTORY_LIMIT);
  };

  const clearHistory = (): void => {
    undoStack.value = [];
    redoStack.value = [];
  };

  const applyState = (
    nextState: PlaytestState,
    options: ApplyPlaytestStateOptions = {},
  ): void => {
    const currentState = playtest.value;
    if (nextState === currentState) {
      return;
    }
    if (currentState && options.recordHistory !== false) {
      pushUndoState(currentState);
      redoStack.value = [];
    }
    playtest.value = nextState;
    pruneState(nextState);
  };

  const replacePlaytestState = (nextState: PlaytestState | null): void => {
    playtest.value = nextState;
    clearHistory();
    if (nextState) {
      pruneState(nextState);
    } else {
      clearSelection();
    }
  };

  const undoPlaytestState = (): boolean => {
    if (!playtest.value || undoStack.value.length === 0) {
      return false;
    }
    const previousState = undoStack.value[undoStack.value.length - 1];
    if (!previousState) {
      return false;
    }
    undoStack.value = undoStack.value.slice(0, -1);
    pushRedoState(playtest.value);
    clearTransientUi();
    applyState(previousState, { recordHistory: false });
    return true;
  };

  const redoPlaytestState = (): boolean => {
    if (!playtest.value || redoStack.value.length === 0) {
      return false;
    }
    const nextState = redoStack.value[redoStack.value.length - 1];
    if (!nextState) {
      return false;
    }
    redoStack.value = redoStack.value.slice(0, -1);
    pushUndoState(playtest.value);
    clearTransientUi();
    applyState(nextState, { recordHistory: false });
    return true;
  };

  return {
    applyState,
    clearHistory,
    redoStack,
    redoPlaytestState,
    replacePlaytestState,
    undoStack,
    undoPlaytestState,
  };
};
