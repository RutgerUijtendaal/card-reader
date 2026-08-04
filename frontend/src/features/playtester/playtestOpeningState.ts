import type { DeckRecord } from '@/domain/decks/types';
import type {
  PlaytestCardInstance,
  PlaytestOpeningSetup,
  PlaytestOpeningStep,
  PlaytestSetupSnapshot,
  PlaytestState,
  PlaytestZoneId,
} from '@/features/playtester/types';
import {
  cloneInstances,
  countZone,
  createInitialPlaytestState,
  EMPTY_OPENING_SETUP,
  getZoneInstances,
  isManaCardInstance,
  isSetupCardInstance,
  openingManaSetupWith,
  renumberAllZones,
  selectedOpeningIds,
  selectedOpeningIdsFromSetup,
  setupCardIds,
  shuffleInstances,
  syncOpeningSelections,
  uniqueIds,
} from '@/features/playtester/playtestStateCore';
import {
  moveInstanceToZone,
  placeInstanceOnBoard,
  trimOpeningHandToSize,
} from '@/features/playtester/playtestBoardState';

export const drawUpToOpeningHandSize = (state: PlaytestState): PlaytestState => {
  let nextState = trimOpeningHandToSize(state);
  const reservedIds = selectedOpeningIds(nextState);
  while (countZone(nextState, 'hand') < nextState.handSize) {
    const topCard = getZoneInstances(nextState, 'library').find((instance) => !reservedIds.has(instance.instanceId));
    if (!topCard) {
      break;
    }
    nextState = moveInstanceToZone(nextState, topCard.instanceId, 'hand');
  }
  return nextState;
};

export const getOpeningManaInstances = (state: PlaytestState): PlaytestCardInstance[] =>
  {
    const selectedIds = new Set(state.openingSetup.selectedManaInstanceIds);
    return state.instances
      .filter((instance) =>
        isManaCardInstance(instance)
        && (instance.zoneId === 'library' || selectedIds.has(instance.instanceId)),
      )
      .sort((left, right) => left.card.name.localeCompare(right.card.name) || left.instanceId.localeCompare(right.instanceId));
  };

export const getOpeningSetupInstances = (state: PlaytestState): PlaytestCardInstance[] =>
  state.instances
    .filter((instance) => instance.zoneId !== 'hero' && isSetupCardInstance(instance))
    .sort((left, right) => left.card.name.localeCompare(right.card.name) || left.instanceId.localeCompare(right.instanceId));

const setOpeningReservation = (
  state: PlaytestState,
  instanceId: string,
  selected: boolean,
): PlaytestState => {
  const instance = state.instances.find((entry) => entry.instanceId === instanceId);
  if (!instance || instance.zoneId === 'hero') {
    return state;
  }
  const currentOrigins = state.openingSetup.reservedOrigins ?? {};
  const currentOriginOrders = state.openingSetup.reservedOriginOrders ?? {};
  const nextSetupWithoutOrigins = openingManaSetupWith(state.openingSetup, instanceId, selected);
  const nextSelectedIds = selectedOpeningIdsFromSetup(nextSetupWithoutOrigins);
  const nextOrigins: Partial<Record<string, PlaytestZoneId>> = {
    ...currentOrigins,
    ...(selected ? { [instanceId]: currentOrigins[instanceId] ?? instance.zoneId } : {}),
  };
  const nextOriginOrders: Partial<Record<string, number>> = {
    ...currentOriginOrders,
    ...(selected ? { [instanceId]: currentOriginOrders[instanceId] ?? instance.order } : {}),
  };
  if (!nextSelectedIds.has(instanceId)) {
    delete nextOrigins[instanceId];
    delete nextOriginOrders[instanceId];
  }
  const openingSetup: PlaytestOpeningSetup = {
    ...nextSetupWithoutOrigins,
    reservedOrigins: nextOrigins,
    reservedOriginOrders: nextOriginOrders,
  };
  if (selected || nextSelectedIds.has(instanceId)) {
    return moveInstanceToZone({ ...state, openingSetup }, instanceId, 'other');
  }

  const origin = currentOrigins[instanceId] ?? 'library';
  const nextState = { ...state, openingSetup };
  return moveInstanceToZone(nextState, instanceId, origin, currentOriginOrders[instanceId]);
};

export const toggleOpeningManaSelection = (
  state: PlaytestState,
  instanceId: string,
  selected: boolean,
): PlaytestState =>
  setOpeningReservation(state, instanceId, selected);

export const mulliganOpeningHand = (
  state: PlaytestState,
  random: () => number = Math.random,
): PlaytestState => {
  const syncedState = syncOpeningSelections(state);
  const selectedIds = selectedOpeningIds(syncedState);
  const reservedOrigins: Partial<Record<string, PlaytestZoneId>> = {
    ...(syncedState.openingSetup.reservedOrigins ?? {}),
  };
  const reservedOriginOrders: Partial<Record<string, number>> = {
    ...(syncedState.openingSetup.reservedOriginOrders ?? {}),
  };
  selectedIds.forEach((instanceId) => {
    reservedOrigins[instanceId] = 'library';
    delete reservedOriginOrders[instanceId];
  });
  const returnedHand = syncedState.instances.map((instance) =>
    instance.zoneId === 'hand' && !selectedIds.has(instance.instanceId) && !instance.setupOrigin
      ? {
          ...instance,
          zoneId: 'library' as const,
          tapped: false,
          boardX: null,
          boardY: null,
          pileGroupId: null,
          pileOrder: null,
        }
      : instance,
  );
  const library = shuffleInstances(
    returnedHand.filter((instance) => instance.zoneId === 'library' && !selectedIds.has(instance.instanceId)),
    random,
  );
  const libraryById = new Map(library.map((instance) => [instance.instanceId, instance]));
  const nextInstances = returnedHand.map((instance) => libraryById.get(instance.instanceId) ?? instance);

  return drawUpToOpeningHandSize({
    ...syncedState,
    phase: 'opening',
    openingSetup: {
      ...syncedState.openingSetup,
      step: 'hand',
      mulliganCount: (syncedState.openingSetup.mulliganCount ?? 0) + 1,
      reservedOrigins,
      reservedOriginOrders,
    },
    instances: renumberAllZones(nextInstances),
  });
};

export const setOpeningStep = (
  state: PlaytestState,
  step: PlaytestOpeningStep,
): PlaytestState => {
  const syncedState = syncOpeningSelections(state);
  const nextInstances = syncedState.phase === 'opening' && syncedState.openingSetup.step === 'hand' && step !== 'hand'
    ? renumberAllZones(syncedState.instances.map((instance) =>
        instance.zoneId === 'hand' && !instance.setupOrigin
          ? {
              ...instance,
              zoneId: 'library' as const,
              tapped: false,
              boardX: null,
              boardY: null,
              pileGroupId: null,
              pileOrder: null,
            }
          : instance,
      ))
    : syncedState.instances;
  return {
    ...syncedState,
    phase: 'opening',
    instances: nextInstances,
    openingSetup: {
      ...syncedState.openingSetup,
      step,
    },
  };
};

export const drawOpeningHand = (state: PlaytestState): PlaytestState =>
  drawUpToOpeningHandSize(setOpeningStep(state, 'hand'));

export const toggleOpeningSetupHandled = (
  state: PlaytestState,
  cardId: string,
  handled: boolean,
): PlaytestState => {
  if (!setupCardIds(state.instances).has(cardId)) {
    return state;
  }
  const current = state.openingSetup.handledSetupCardIds ?? [];
  return {
    ...state,
    openingSetup: {
      ...state.openingSetup,
      handledSetupCardIds: handled
        ? uniqueIds([...current, cardId])
        : current.filter((id) => id !== cardId),
    },
  };
};

export const stageOpeningSetupCardForPlay = (
  state: PlaytestState,
  instanceId: string,
): PlaytestState => {
  const instance = state.instances.find((entry) => entry.instanceId === instanceId);
  if (!instance || instance.zoneId === 'hero') {
    return state;
  }
  const movedState = moveInstanceToZone(state, instanceId, 'other');
  return {
    ...movedState,
    openingSetup: {
      ...movedState.openingSetup,
      selectedSetupInstanceIds: uniqueIds([...movedState.openingSetup.selectedSetupInstanceIds, instanceId]),
    },
    instances: movedState.instances.map((entry) =>
      entry.instanceId === instanceId
        ? { ...entry, setupOrigin: true }
        : entry,
    ),
  };
};

export const acceptOpeningSetup = (state: PlaytestState): PlaytestState => {
  const syncedState = syncOpeningSelections(state);
  const selectedManaIds = syncedState.openingSetup.selectedManaInstanceIds;
  const selectedSetupIds = syncedState.openingSetup.selectedSetupInstanceIds;
  const selectedIds = [...selectedManaIds, ...selectedSetupIds];
  const selectedIdSet = new Set(selectedIds);
  let nextState = syncedState;
  selectedIds.forEach((instanceId, index) => {
    nextState = placeInstanceOnBoard(nextState, instanceId, 12 + (index % 6) * 8, 78 - Math.floor(index / 6) * 13);
  });
  const setupInstances = nextState.instances.map((instance) => ({
    ...instance,
    setupOrigin: instance.setupOrigin || instance.zoneId === 'hero' || selectedIdSet.has(instance.instanceId),
  }));
  const setupSnapshot: PlaytestSetupSnapshot = {
    instances: cloneInstances(setupInstances),
  };
  return {
    ...nextState,
    phase: 'play',
    instances: setupInstances,
    openingSetup: { ...EMPTY_OPENING_SETUP },
    setupSnapshot,
  };
};

export const resetToSetup = (state: PlaytestState): PlaytestState => {
  if (!state.setupSnapshot) {
    return state;
  }
  return {
    ...state,
    phase: 'play',
    instances: cloneInstances(state.setupSnapshot.instances),
  };
};

const setHandSize = (state: PlaytestState, handSize: number): PlaytestState => ({
  ...state,
  handSize: Math.max(0, Math.min(99, Math.trunc(handSize))),
});

export const setOpeningHandSize = (state: PlaytestState, handSize: number): PlaytestState =>
  state.openingSetup.step === 'hand'
    ? drawUpToOpeningHandSize(setHandSize(state, handSize))
    : setHandSize(state, handSize);

export const createOpeningHandPreviewState = (
  deck: DeckRecord,
  random: () => number = Math.random,
): PlaytestState =>
  drawUpToOpeningHandSize({
    ...createInitialPlaytestState(deck, random),
    openingSetup: { ...EMPTY_OPENING_SETUP, step: 'hand' },
  });
