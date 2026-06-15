import type { DeckEntrySummary, DeckRecord } from '@/modules/decks/types';
import type {
  PlaytestCardFace,
  PlaytestCardInstance,
  PlaytestOpeningSetup,
  PlaytestSetupSnapshot,
  PlaytestStackFace,
  PlaytestState,
  PlaytestZoneId,
  StoredPlaytestDraft,
} from '@/modules/playtester/types';

export const DEFAULT_PLAYTEST_HAND_SIZE = 7;
export const PLAYTEST_ZONES: PlaytestZoneId[] = ['hero', 'library', 'hand', 'play', 'discard', 'banish', 'other'];
export const PLAYTEST_DRAFT_VERSION = 2;
export const DEFAULT_PLAYTEST_STACK_FACES: Partial<Record<PlaytestZoneId, PlaytestStackFace>> = {
  library: 'back',
  discard: 'front',
  banish: 'front',
  other: 'front',
};
export const EMPTY_OPENING_SETUP: PlaytestOpeningSetup = {
  selectedManaInstanceIds: [],
  selectedSetupInstanceIds: [],
  reservedOrigins: {},
  reservedOriginOrders: {},
};

type OpeningSelectionKey = 'selectedManaInstanceIds' | 'selectedSetupInstanceIds';
type ClonePlacement =
  | { type: 'after-source' }
  | { type: 'board'; anchorX: number; anchorY: number };

type LegacyPlaytestCardInstance = Omit<PlaytestCardInstance, 'face'> & {
  face?: PlaytestCardFace;
};

const cloneInstances = (instances: PlaytestCardInstance[]): PlaytestCardInstance[] =>
  normalizePileGroups(instances.map((instance) => ({ ...instance })));

const normalizeInstanceFields = (instance: LegacyPlaytestCardInstance): PlaytestCardInstance => ({
  ...instance,
  face: instance.face ?? 'front',
});

const orderedZoneInstances = (
  instances: PlaytestCardInstance[],
  zoneId: PlaytestZoneId,
): PlaytestCardInstance[] =>
  instances
    .filter((instance) => instance.zoneId === zoneId)
    .sort((left, right) => left.order - right.order || left.instanceId.localeCompare(right.instanceId));

const renumberZone = (
  instances: PlaytestCardInstance[],
  zoneId: PlaytestZoneId,
): PlaytestCardInstance[] => {
  const orderedIds = orderedZoneInstances(instances, zoneId).map((instance) => instance.instanceId);
  const orderById = new Map(orderedIds.map((id, index) => [id, index]));
  return instances.map((instance) =>
    instance.zoneId === zoneId
      ? {
          ...instance,
          order: orderById.get(instance.instanceId) ?? instance.order,
        }
      : instance,
  );
};

const renumberAllZones = (instances: PlaytestCardInstance[]): PlaytestCardInstance[] =>
  PLAYTEST_ZONES.reduce((current, zoneId) => renumberZone(current, zoneId), instances);

const uniqueIds = (ids: string[]): string[] => [...new Set(ids)];

const selectedOpeningIds = (state: PlaytestState): Set<string> =>
  new Set([
    ...state.openingSetup.selectedManaInstanceIds,
    ...state.openingSetup.selectedSetupInstanceIds,
  ]);

const openingSetupWith = (
  setup: PlaytestOpeningSetup,
  key: OpeningSelectionKey,
  instanceId: string,
  selected: boolean,
): PlaytestOpeningSetup => ({
  ...setup,
  [key]: selected
    ? uniqueIds([...setup[key], instanceId])
    : setup[key].filter((id) => id !== instanceId),
});

const selectedOpeningIdsFromSetup = (setup: PlaytestOpeningSetup): Set<string> =>
  new Set([
    ...setup.selectedManaInstanceIds,
    ...setup.selectedSetupInstanceIds,
  ]);

const syncOpeningSelections = (state: PlaytestState): PlaytestState => {
  const ids = new Set(state.instances.map((instance) => instance.instanceId));
  const selectedIds = selectedOpeningIdsFromSetup(state.openingSetup);
  const reservedOrigins = Object.fromEntries(
    Object.entries(state.openingSetup.reservedOrigins ?? {})
      .filter(([id]) => ids.has(id) && selectedIds.has(id)),
  );
  const reservedOriginOrders = Object.fromEntries(
    Object.entries(state.openingSetup.reservedOriginOrders ?? {})
      .filter(([id]) => ids.has(id) && selectedIds.has(id)),
  );
  return {
    ...state,
    openingSetup: {
      selectedManaInstanceIds: state.openingSetup.selectedManaInstanceIds.filter((id) => ids.has(id)),
      selectedSetupInstanceIds: state.openingSetup.selectedSetupInstanceIds.filter((id) => ids.has(id)),
      reservedOrigins,
      reservedOriginOrders,
    },
  };
};

export const normalizePileGroups = (instances: PlaytestCardInstance[]): PlaytestCardInstance[] => {
  const groups = new Map<string, PlaytestCardInstance[]>();

  for (const instance of instances) {
    if (instance.zoneId !== 'play' || !instance.pileGroupId) {
      continue;
    }
    groups.set(instance.pileGroupId, [...(groups.get(instance.pileGroupId) ?? []), instance]);
  }

  const normalizedById = new Map<string, PlaytestCardInstance>();
  for (const [groupId, members] of groups) {
    if (members.length < 2) {
      for (const member of members) {
        normalizedById.set(member.instanceId, {
          ...member,
          pileGroupId: null,
          pileOrder: null,
        });
      }
      continue;
    }

    const ordered = [...members].sort(
      (left, right) =>
        (left.pileOrder ?? left.order) - (right.pileOrder ?? right.order)
        || left.instanceId.localeCompare(right.instanceId),
    );
    const anchor = ordered[0];
    const anchorX = anchor?.boardX ?? 16;
    const anchorY = anchor?.boardY ?? 22;

    ordered.forEach((member, index) => {
      normalizedById.set(member.instanceId, {
        ...member,
        boardX: anchorX,
        boardY: anchorY,
        pileGroupId: groupId,
        pileOrder: index,
      });
    });
  }

  return instances.map((instance) => normalizedById.get(instance.instanceId) ?? instance);
};

const buildMainboardInstances = (entries: DeckEntrySummary[]): PlaytestCardInstance[] =>
  entries.flatMap((entry) =>
    Array.from({ length: entry.quantity }, (_, index) => ({
      instanceId: `${entry.card.id}:main:${index + 1}`,
      cardId: entry.card.id,
      card: entry.card,
      zoneId: 'library' as const,
      order: 0,
      tapped: false,
      face: 'front' as const,
      setupOrigin: false,
      boardX: null,
      boardY: null,
      pileGroupId: null,
      pileOrder: null,
    })),
  ).map((instance, index) => ({
    ...instance,
    order: index,
  }));

export const shuffleInstances = (
  instances: PlaytestCardInstance[],
  random: () => number = Math.random,
): PlaytestCardInstance[] => {
  const next = [...instances];
  for (let index = next.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    const current = next[index];
    const swap = next[swapIndex];
    if (!current || !swap) continue;
    next[index] = swap;
    next[swapIndex] = current;
  }
  return next.map((instance, index) => ({ ...instance, order: index }));
};

export const createInitialPlaytestState = (
  deck: DeckRecord,
  random: () => number = Math.random,
): PlaytestState => drawUpToOpeningHandSize({
  deckId: deck.id,
  deckUpdatedAt: deck.updated_at,
  phase: 'opening',
  handSize: DEFAULT_PLAYTEST_HAND_SIZE,
  stackFaces: { ...DEFAULT_PLAYTEST_STACK_FACES },
  openingSetup: { ...EMPTY_OPENING_SETUP },
  instances: renumberAllZones([
    {
      instanceId: `${deck.hero_card.id}:hero:1`,
      cardId: deck.hero_card.id,
      card: deck.hero_card,
      zoneId: 'hero',
      order: 0,
      tapped: false,
      face: 'front',
      setupOrigin: true,
      boardX: null,
      boardY: null,
      pileGroupId: null,
      pileOrder: null,
    },
    ...shuffleInstances(buildMainboardInstances(deck.mainboard.entries), random),
  ]),
  setupSnapshot: null,
});

export const setStackFace = (
  state: PlaytestState,
  zoneId: PlaytestZoneId,
  face: PlaytestStackFace,
): PlaytestState => ({
  ...state,
  stackFaces: {
    ...DEFAULT_PLAYTEST_STACK_FACES,
    ...state.stackFaces,
    [zoneId]: face,
  },
});

export const countZone = (state: PlaytestState, zoneId: PlaytestZoneId): number =>
  state.instances.filter((instance) => instance.zoneId === zoneId).length;

export const getZoneInstances = (
  state: PlaytestState,
  zoneId: PlaytestZoneId,
): PlaytestCardInstance[] => orderedZoneInstances(state.instances, zoneId);

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

const trimOpeningHandToSize = (state: PlaytestState): PlaytestState => {
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

export const isManaCardInstance = (instance: PlaytestCardInstance): boolean =>
  instance.card.types.some((type) => type.key.trim().toLowerCase() === 'mana');

export const isSetupCardInstance = (instance: PlaytestCardInstance): boolean =>
  instance.card.keywords.some((keyword) => keyword.trim().toLowerCase() === 'setup');

export const getOpeningManaInstances = (state: PlaytestState): PlaytestCardInstance[] =>
  state.instances
    .filter((instance) => instance.zoneId !== 'hero' && isManaCardInstance(instance))
    .sort((left, right) => left.card.name.localeCompare(right.card.name) || left.instanceId.localeCompare(right.instanceId));

export const getOpeningSetupInstances = (state: PlaytestState): PlaytestCardInstance[] =>
  state.instances
    .filter((instance) => instance.zoneId !== 'hero' && isSetupCardInstance(instance))
    .sort((left, right) => left.card.name.localeCompare(right.card.name) || left.instanceId.localeCompare(right.instanceId));

const setOpeningReservation = (
  state: PlaytestState,
  instanceId: string,
  key: OpeningSelectionKey,
  selected: boolean,
): PlaytestState => {
  const instance = state.instances.find((entry) => entry.instanceId === instanceId);
  if (!instance || instance.zoneId === 'hero') {
    return state;
  }
  const currentOrigins = state.openingSetup.reservedOrigins ?? {};
  const currentOriginOrders = state.openingSetup.reservedOriginOrders ?? {};
  const nextSetupWithoutOrigins = openingSetupWith(state.openingSetup, key, instanceId, selected);
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
    return drawUpToOpeningHandSize(moveInstanceToZone({ ...state, openingSetup }, instanceId, 'other'));
  }

  const origin = currentOrigins[instanceId] ?? 'library';
  let nextState = { ...state, openingSetup };
  if (origin === 'hand' && state.handSize > 0) {
    const reservedIds = selectedOpeningIds(nextState);
    const replacement = [...getZoneInstances(nextState, 'hand')]
      .reverse()
      .find((entry) => !reservedIds.has(entry.instanceId));
    if (replacement && countZone(nextState, 'hand') >= state.handSize) {
      nextState = moveInstanceToZone(nextState, replacement.instanceId, 'library', 0);
    }
    return drawUpToOpeningHandSize(moveInstanceToZone(nextState, instanceId, 'hand', currentOriginOrders[instanceId]));
  }

  return drawUpToOpeningHandSize(moveInstanceToZone(nextState, instanceId, 'library'));
};

export const toggleOpeningManaSelection = (
  state: PlaytestState,
  instanceId: string,
  selected: boolean,
): PlaytestState =>
  setOpeningReservation(state, instanceId, 'selectedManaInstanceIds', selected);

export const toggleOpeningSetupSelection = (
  state: PlaytestState,
  instanceId: string,
  selected: boolean,
): PlaytestState =>
  setOpeningReservation(state, instanceId, 'selectedSetupInstanceIds', selected);

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
    instance.zoneId === 'hand' && !selectedIds.has(instance.instanceId)
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
      reservedOrigins,
      reservedOriginOrders,
    },
    instances: renumberAllZones(nextInstances),
  });
};

export const acceptOpeningSetup = (state: PlaytestState): PlaytestState => {
  const syncedState = syncOpeningSelections(state);
  const selectedManaIds = syncedState.openingSetup.selectedManaInstanceIds;
  const selectedSetupIds = syncedState.openingSetup.selectedSetupInstanceIds;
  const selectedIds = [...selectedManaIds, ...selectedSetupIds];
  const selectedIdSet = new Set(selectedIds);
  let nextState = syncedState;
  selectedManaIds.forEach((instanceId, index) => {
    nextState = placeInstanceOnBoard(nextState, instanceId, 12 + (index % 6) * 8, 78 - Math.floor(index / 6) * 13);
  });
  selectedSetupIds.forEach((instanceId, index) => {
    nextState = placeInstanceOnBoard(nextState, instanceId, 88 - (index % 6) * 8, 78 - Math.floor(index / 6) * 13);
  });
  const setupInstances = nextState.instances.map((instance) => ({
    ...instance,
    setupOrigin: instance.zoneId === 'hero' || selectedIdSet.has(instance.instanceId),
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
  drawUpToOpeningHandSize(setHandSize(state, handSize));

export const serializePlaytestDraft = (state: PlaytestState): StoredPlaytestDraft => ({
  version: PLAYTEST_DRAFT_VERSION,
  deckId: state.deckId,
  deckUpdatedAt: state.deckUpdatedAt,
  state: {
    ...state,
    instances: normalizePileGroups(state.instances),
    openingSetup: syncOpeningSelections(state).openingSetup,
    setupSnapshot: state.setupSnapshot
      ? { instances: normalizePileGroups(state.setupSnapshot.instances) }
      : null,
  },
  savedAt: new Date().toISOString(),
});

type LegacyPlaytestState = Omit<PlaytestState, 'instances' | 'setupSnapshot'> & {
  instances: LegacyPlaytestCardInstance[];
  setupSnapshot: null | { instances: LegacyPlaytestCardInstance[] };
};

type LegacyStoredPlaytestDraft = Omit<StoredPlaytestDraft, 'version' | 'state'> & {
  version: 1 | 2;
  state: LegacyPlaytestState;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object';

const migratePlaytestState = (state: LegacyPlaytestState): PlaytestState => ({
  ...state,
  openingSetup: {
    ...EMPTY_OPENING_SETUP,
    ...state.openingSetup,
  },
  instances: normalizePileGroups(renumberAllZones(state.instances.map(normalizeInstanceFields))),
  setupSnapshot: state.setupSnapshot
    ? { instances: normalizePileGroups(renumberAllZones(state.setupSnapshot.instances.map(normalizeInstanceFields))) }
    : null,
});

export const migrateStoredPlaytestDraft = (value: unknown): StoredPlaytestDraft | null => {
  if (!isRecord(value)) {
    return null;
  }
  if (value.version !== 1 && value.version !== PLAYTEST_DRAFT_VERSION) {
    return null;
  }
  if (typeof value.deckId !== 'string' || !isRecord(value.state)) {
    return null;
  }
  if (!Array.isArray(value.state.instances)) {
    return null;
  }

  const legacyDraft = value as unknown as LegacyStoredPlaytestDraft;
  return {
    ...legacyDraft,
    version: PLAYTEST_DRAFT_VERSION,
    deckUpdatedAt: typeof legacyDraft.deckUpdatedAt === 'string' ? legacyDraft.deckUpdatedAt : '',
    savedAt: typeof legacyDraft.savedAt === 'string' ? legacyDraft.savedAt : new Date(0).toISOString(),
    state: migratePlaytestState(legacyDraft.state),
  };
};

export const isStoredDraftStale = (draft: StoredPlaytestDraft, deck: DeckRecord): boolean =>
  draft.deckUpdatedAt !== deck.updated_at;
