import type { Ref } from 'vue';
import type {
  PlaytestOpeningStep,
  PlaytestState,
  PlaytestZoneId,
} from '@/features/playtester/types';
import {
  acceptOpeningSetup,
  drawOpeningHand,
  mulliganOpeningHand,
  setOpeningHandSize,
  setOpeningStep,
  stageOpeningSetupCardForPlay,
  toggleOpeningManaSelection,
  toggleOpeningSetupHandled,
} from '@/features/playtester/playtestOpeningState';
import { STARTING_MANA_REQUIRED } from '@/features/playtester/playtestStateCore';

type ApplyState = (
  state: PlaytestState,
  options?: { recordHistory?: boolean },
) => void;

type UsePlaytestOpeningFlowOptions = {
  playtest: Ref<PlaytestState | null>;
  applyState: ApplyState;
  clearHistory: () => void;
  closeStack: () => void;
  moveOpeningTransferCard: (
    state: PlaytestState,
    instanceId: string,
    zoneId: PlaytestZoneId,
  ) => PlaytestState;
};

export const usePlaytestOpeningFlow = ({
  playtest,
  applyState,
  clearHistory,
  closeStack,
  moveOpeningTransferCard,
}: UsePlaytestOpeningFlowOptions) => {
  const applyWithoutHistory = (state: PlaytestState): void => {
    applyState(state, { recordHistory: false });
  };

  const updateOpeningHandSize = (handSize: number): void => {
    if (playtest.value) applyWithoutHistory(setOpeningHandSize(playtest.value, handSize));
  };
  const toggleOpeningMana = (instanceId: string, selected: boolean): void => {
    if (playtest.value) {
      applyWithoutHistory(toggleOpeningManaSelection(playtest.value, instanceId, selected));
    }
  };
  const toggleOpeningSetupCardHandled = (cardId: string, handled: boolean): void => {
    if (playtest.value) {
      applyWithoutHistory(toggleOpeningSetupHandled(playtest.value, cardId, handled));
    }
  };
  const continueOpeningMana = (): void => {
    const state = playtest.value;
    if (!state || state.openingSetup.selectedManaInstanceIds.length !== STARTING_MANA_REQUIRED) return;
    closeStack();
    applyWithoutHistory(setOpeningStep(state, 'setup'));
  };
  const continueOpeningSetup = (): void => {
    if (!playtest.value) return;
    closeStack();
    applyWithoutHistory(drawOpeningHand(playtest.value));
  };
  const previousOpeningStep = (): void => {
    const state = playtest.value;
    if (!state) return;
    if (state.openingSetup.step === 'setup') applyWithoutHistory(setOpeningStep(state, 'mana'));
    else if (state.openingSetup.step === 'hand') applyWithoutHistory(setOpeningStep(state, 'setup'));
  };
  const selectOpeningStep = (targetStep: PlaytestOpeningStep): void => {
    const state = playtest.value;
    if (!state || state.phase !== 'opening') return;
    const steps: PlaytestOpeningStep[] = ['mana', 'setup', 'hand'];
    const currentIndex = steps.indexOf(state.openingSetup.step);
    const targetIndex = steps.indexOf(targetStep);
    if (targetIndex < 0 || currentIndex < 0 || targetIndex >= currentIndex) return;
    closeStack();
    applyWithoutHistory(setOpeningStep(state, targetStep));
  };
  const moveOpeningSetupCard = (instanceId: string, zoneId: PlaytestZoneId): void => {
    const state = playtest.value;
    if (!state) return;
    applyState(
      zoneId === 'play'
        ? stageOpeningSetupCardForPlay(state, instanceId)
        : moveOpeningTransferCard(state, instanceId, zoneId),
    );
  };
  const mulliganOpeningSetup = (): void => {
    const state = playtest.value;
    if (state?.openingSetup.step === 'hand') applyWithoutHistory(mulliganOpeningHand(state));
  };
  const keepOpeningSetup = (): void => {
    const state = playtest.value;
    if (state?.openingSetup.step !== 'hand') return;
    clearHistory();
    applyWithoutHistory(acceptOpeningSetup(state));
  };

  return {
    updateOpeningHandSize,
    toggleOpeningMana,
    toggleOpeningSetupCardHandled,
    continueOpeningMana,
    continueOpeningSetup,
    previousOpeningStep,
    selectOpeningStep,
    moveOpeningSetupCard,
    mulliganOpeningSetup,
    keepOpeningSetup,
  };
};
