import type { PlaytestCardInstance, PlaytestState, PlaytestZoneId } from '@/features/playtester/types';
import {
  countZone,
  getZoneInstances,
  normalizePileGroups,
  orderedZoneInstances,
  renumberAllZones,
  selectedOpeningIds,
  shuffleInstances,
  syncOpeningSelections,
} from '@/features/playtester/playtestStateCore';

type ClonePlacement =
  | { type: 'after-source' }
  | { type: 'board'; anchorX: number; anchorY: number };

export const moveInstanceToZone = (
  state: PlaytestState,
  instanceId: string,
  zoneId: PlaytestZoneId,
  targetIndex?: number,
): PlaytestState => {
  const moving = state.instances.find((instance) => instance.instanceId === instanceId);
  if (!moving) {
    return state;
  }

  const remaining = state.instances.filter((instance) => instance.instanceId !== instanceId);
  const destination = orderedZoneInstances(remaining, zoneId);
  const insertionIndex = Math.max(0, Math.min(targetIndex ?? destination.length, destination.length));
  const moved = {
    ...moving,
    zoneId,
    tapped: zoneId === 'play' ? moving.tapped : false,
    boardX: zoneId === 'play' ? moving.boardX : null,
    boardY: zoneId === 'play' ? moving.boardY : null,
    pileGroupId: null,
    pileOrder: null,
  };

  destination.splice(insertionIndex, 0, moved);
  const destinationIds = new Set(destination.map((instance) => instance.instanceId));
  const destinationById = new Map(
    destination.map((instance, index) => [
      instance.instanceId,
      {
        ...instance,
        order: index,
      },
    ]),
  );

  return {
    ...state,
    instances: normalizePileGroups(renumberAllZones([
      ...remaining.filter((instance) => !destinationIds.has(instance.instanceId)),
      ...[...destinationById.values()],
    ])),
  };
};

export const placeInstanceOnBoard = (
  state: PlaytestState,
  instanceId: string,
  boardX: number,
  boardY: number,
): PlaytestState => {
  const nextState = moveInstanceToZone(state, instanceId, 'play');
  return {
    ...nextState,
    instances: nextState.instances.map((instance) =>
      instance.instanceId === instanceId
        ? {
          ...instance,
          boardX: Math.max(0, Math.min(100, boardX)),
          boardY: Math.max(0, Math.min(100, boardY)),
          pileGroupId: null,
          pileOrder: null,
        }
        : instance,
    ),
  };
};

export const moveBoardInstancesByDelta = (
  state: PlaytestState,
  instanceIds: string[],
  deltaX: number,
  deltaY: number,
): PlaytestState => {
  const selectedIds = new Set(instanceIds);
  return {
    ...state,
    instances: normalizePileGroups(state.instances.map((instance) => {
      if (instance.zoneId !== 'play' || !selectedIds.has(instance.instanceId)) {
        return instance;
      }
      return {
        ...instance,
        boardX: Math.max(0, Math.min(100, (instance.boardX ?? 16) + deltaX)),
        boardY: Math.max(0, Math.min(100, (instance.boardY ?? 22) + deltaY)),
      };
    })),
  };
};

export const addInstanceToVisualPile = (
  state: PlaytestState,
  instanceId: string,
  targetInstanceId: string,
): PlaytestState => {
  if (instanceId === targetInstanceId) {
    return state;
  }
  const moving = state.instances.find((instance) => instance.instanceId === instanceId);
  const target = state.instances.find((instance) => instance.instanceId === targetInstanceId);
  if (!moving || !target || target.zoneId !== 'play') {
    return state;
  }

  const targetGroupId = target.pileGroupId ?? `pile:${target.instanceId}`;
  const groupMembers = state.instances
    .filter((instance) => instance.zoneId === 'play' && instance.pileGroupId === targetGroupId)
    .sort((left, right) => (left.pileOrder ?? left.order) - (right.pileOrder ?? right.order));
  const nextOrder = Math.max(0, ...groupMembers.map((instance) => instance.pileOrder ?? 0)) + 1;
  const anchor = groupMembers[0] ?? target;
  const anchorX = anchor.boardX ?? target.boardX ?? 16;
  const anchorY = anchor.boardY ?? target.boardY ?? 22;

  return {
    ...state,
    instances: normalizePileGroups(renumberAllZones(state.instances.map((instance) => {
      if (instance.instanceId === target.instanceId) {
        return {
          ...instance,
          zoneId: 'play',
          boardX: anchorX,
          boardY: anchorY,
          pileGroupId: targetGroupId,
          pileOrder: instance.pileOrder ?? 0,
        };
      }
      if (instance.instanceId === moving.instanceId) {
        return {
          ...instance,
          zoneId: 'play',
          tapped: moving.zoneId === 'play' ? moving.tapped : false,
          boardX: anchorX,
          boardY: anchorY,
          pileGroupId: targetGroupId,
          pileOrder: nextOrder,
        };
      }
      return instance;
    }))),
  };
};

export const groupInstancesIntoVisualPile = (
  state: PlaytestState,
  instanceIds: string[],
): PlaytestState => {
  const uniqueIds = [...new Set(instanceIds)];
  const boardIds = uniqueIds.filter((instanceId) =>
    state.instances.some((instance) => instance.instanceId === instanceId && instance.zoneId === 'play'),
  );
  const [anchorId, ...memberIds] = boardIds;
  if (!anchorId || memberIds.length === 0) {
    return state;
  }

  return memberIds.reduce((nextState, memberId) => {
    const anchor = nextState.instances.find((instance) => instance.instanceId === anchorId);
    const member = nextState.instances.find((instance) => instance.instanceId === memberId);
    if (anchor?.pileGroupId && member?.pileGroupId === anchor.pileGroupId) {
      return nextState;
    }
    return addInstanceToVisualPile(nextState, memberId, anchorId);
  }, state);
};

export const removeInstanceFromVisualPile = (
  state: PlaytestState,
  instanceId: string,
  boardX?: number,
  boardY?: number,
): PlaytestState => ({
  ...state,
  instances: normalizePileGroups(state.instances.map((instance) =>
    instance.instanceId === instanceId
      ? {
          ...instance,
          boardX: boardX ?? instance.boardX,
          boardY: boardY ?? instance.boardY,
          pileGroupId: null,
          pileOrder: null,
        }
      : instance,
  )),
});

export const toggleTapped = (state: PlaytestState, instanceId: string): PlaytestState => ({
  ...state,
  instances: state.instances.map((instance) =>
    instance.instanceId === instanceId && instance.zoneId === 'play'
      ? { ...instance, tapped: !instance.tapped }
      : instance,
  ),
});

export const toggleCardFace = (state: PlaytestState, instanceId: string): PlaytestState => ({
  ...state,
  instances: state.instances.map((instance) =>
    instance.instanceId === instanceId
      ? { ...instance, face: instance.face === 'front' ? 'back' : 'front' }
      : instance,
  ),
});

export const toggleCardsFace = (state: PlaytestState, instanceIds: string[]): PlaytestState =>
  instanceIds.reduce((nextState, instanceId) => toggleCardFace(nextState, instanceId), state);

export const deleteCardInstances = (state: PlaytestState, instanceIds: string[]): PlaytestState => {
  const ids = new Set(instanceIds);
  if (ids.size === 0) {
    return state;
  }
  const remaining = state.instances.filter((instance) => !ids.has(instance.instanceId));
  if (remaining.length === state.instances.length) {
    return state;
  }
  return syncOpeningSelections({
    ...state,
    instances: normalizePileGroups(renumberAllZones(remaining)),
  });
};

const nextCloneInstanceId = (state: PlaytestState, sourceInstanceId: string): string => {
  const ids = new Set(state.instances.map((instance) => instance.instanceId));
  let copyNumber = 1;
  let candidate = `${sourceInstanceId}:copy:${copyNumber}`;
  while (ids.has(candidate)) {
    copyNumber += 1;
    candidate = `${sourceInstanceId}:copy:${copyNumber}`;
  }
  return candidate;
};

const insertNewInstanceIntoZone = (
  state: PlaytestState,
  instance: PlaytestCardInstance,
  zoneId: PlaytestZoneId,
  targetIndex?: number,
): PlaytestState => {
  const destination = orderedZoneInstances(state.instances, zoneId);
  const insertionIndex = Math.max(0, Math.min(targetIndex ?? destination.length, destination.length));
  destination.splice(insertionIndex, 0, instance);
  const orderedDestination = destination.map((entry, index) => ({ ...entry, order: index }));
  const destinationIds = new Set(orderedDestination.map((entry) => entry.instanceId));
  return {
    ...state,
    instances: normalizePileGroups(renumberAllZones([
      ...state.instances.filter((entry) => !destinationIds.has(entry.instanceId)),
      ...orderedDestination,
    ])),
  };
};

const cloneSourceInstance = (
  state: PlaytestState,
  source: PlaytestCardInstance,
  zoneId: PlaytestZoneId,
  boardX: number | null,
  boardY: number | null,
): PlaytestCardInstance => ({
  ...source,
  instanceId: nextCloneInstanceId(state, source.instanceId),
  zoneId,
  order: 0,
  tapped: zoneId === 'play' ? source.tapped : false,
  setupOrigin: false,
  boardX: zoneId === 'play' ? boardX : null,
  boardY: zoneId === 'play' ? boardY : null,
  pileGroupId: null,
  pileOrder: null,
});

export const cloneCardInstanceSnapshot = (
  state: PlaytestState,
  source: PlaytestCardInstance,
  placement: ClonePlacement = { type: 'after-source' },
): PlaytestState => {
  if (placement.type === 'board') {
    const clone = cloneSourceInstance(
      state,
      source,
      'play',
      Math.max(0, Math.min(100, placement.anchorX)),
      Math.max(0, Math.min(100, placement.anchorY)),
    );
    return insertNewInstanceIntoZone(state, clone, 'play');
  }

  if (source.zoneId === 'play') {
    const clone = cloneSourceInstance(
      state,
      source,
      'play',
      Math.max(0, Math.min(100, (source.boardX ?? 16) + 4)),
      Math.max(0, Math.min(100, (source.boardY ?? 22) + 4)),
    );
    return insertNewInstanceIntoZone(state, clone, 'play');
  }

  const sourceIndex = getZoneInstances(state, source.zoneId)
    .findIndex((instance) => instance.instanceId === source.instanceId);
  const clone = cloneSourceInstance(state, source, source.zoneId, null, null);
  return insertNewInstanceIntoZone(state, clone, source.zoneId, sourceIndex < 0 ? undefined : sourceIndex + 1);
};

export const cloneCardInstance = (
  state: PlaytestState,
  instanceId: string,
  placement: ClonePlacement = { type: 'after-source' },
): PlaytestState => {
  const source = state.instances.find((instance) => instance.instanceId === instanceId);
  if (!source) {
    return state;
  }

  return cloneCardInstanceSnapshot(state, source, placement);
};

export const cloneCardInstances = (
  state: PlaytestState,
  instanceIds: string[],
  placement: ClonePlacement = { type: 'after-source' },
): PlaytestState => {
  if (placement.type === 'after-source') {
    return instanceIds.reduce((nextState, instanceId) => cloneCardInstance(nextState, instanceId), state);
  }

  const sources = instanceIds.flatMap((instanceId) => {
    const source = state.instances.find((instance) => instance.instanceId === instanceId);
    return source ? [source] : [];
  });
  const baseX = sources[0]?.boardX ?? placement.anchorX;
  const baseY = sources[0]?.boardY ?? placement.anchorY;
  return sources.reduce((nextState, source, index) => {
    const offsetX = source.zoneId === 'play' ? (source.boardX ?? baseX) - baseX : index * 4;
    const offsetY = source.zoneId === 'play' ? (source.boardY ?? baseY) - baseY : index * 4;
    return cloneCardInstance(nextState, source.instanceId, {
      type: 'board',
      anchorX: placement.anchorX + offsetX,
      anchorY: placement.anchorY + offsetY,
    });
  }, state);
};

export const cloneCardInstanceSnapshots = (
  state: PlaytestState,
  sources: PlaytestCardInstance[],
  placement: ClonePlacement = { type: 'after-source' },
): PlaytestState => {
  if (placement.type === 'after-source') {
    return sources.reduce((nextState, source) => cloneCardInstanceSnapshot(nextState, source), state);
  }

  const baseX = sources[0]?.boardX ?? placement.anchorX;
  const baseY = sources[0]?.boardY ?? placement.anchorY;
  return sources.reduce((nextState, source, index) => {
    const offsetX = source.zoneId === 'play' ? (source.boardX ?? baseX) - baseX : index * 4;
    const offsetY = source.zoneId === 'play' ? (source.boardY ?? baseY) - baseY : index * 4;
    return cloneCardInstanceSnapshot(nextState, source, {
      type: 'board',
      anchorX: placement.anchorX + offsetX,
      anchorY: placement.anchorY + offsetY,
    });
  }, state);
};

export const untapAllBoardCards = (state: PlaytestState): PlaytestState => ({
  ...state,
  instances: state.instances.map((instance) =>
    instance.zoneId === 'play' && instance.tapped
      ? { ...instance, tapped: false }
      : instance,
  ),
});

export const drawCards = (state: PlaytestState, count: number): PlaytestState => {
  let nextState = state;
  for (let index = 0; index < count; index += 1) {
    const [topCard] = getZoneInstances(nextState, 'library');
    if (!topCard) {
      break;
    }
    nextState = moveInstanceToZone(nextState, topCard.instanceId, 'hand');
  }
  return nextState;
};

export const startNextTurn = (state: PlaytestState): PlaytestState =>
  drawCards(untapAllBoardCards(state), 1);

export const shuffleZone = (
  state: PlaytestState,
  zoneId: PlaytestZoneId,
  random: () => number = Math.random,
): PlaytestState => {
  const zoneInstances = getZoneInstances(state, zoneId);
  if (zoneInstances.length < 2) {
    return state;
  }
  const shuffled = shuffleInstances(zoneInstances, random);
  const shuffledById = new Map(shuffled.map((instance) => [instance.instanceId, instance]));
  return {
    ...state,
    instances: state.instances.map((instance) => shuffledById.get(instance.instanceId) ?? instance),
  };
};

export const trimOpeningHandToSize = (state: PlaytestState): PlaytestState => {
  let nextState = syncOpeningSelections(state);
  const reservedIds = selectedOpeningIds(nextState);
  while (countZone(nextState, 'hand') > nextState.handSize) {
    const excessCard = [...getZoneInstances(nextState, 'hand')]
      .reverse()
      .find((instance) => !reservedIds.has(instance.instanceId));
    if (!excessCard) {
      break;
    }
    nextState = moveInstanceToZone(nextState, excessCard.instanceId, 'library');
  }
  return nextState;
};

