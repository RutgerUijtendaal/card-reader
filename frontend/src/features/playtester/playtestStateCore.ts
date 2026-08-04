import type { DeckEntrySummary, DeckRecord } from '@/domain/decks/types';
import type {
  PlaytestCardFace,
  PlaytestCardInstance,
  PlaytestOpeningSetup,
  PlaytestStackFace,
  PlaytestState,
  PlaytestZoneId,
} from '@/features/playtester/types';

export const DEFAULT_PLAYTEST_HAND_SIZE = 7;
export const STARTING_MANA_REQUIRED = 3;
export const PLAYTEST_ZONES: PlaytestZoneId[] = ['hero', 'library', 'hand', 'play', 'discard', 'banish', 'other'];
export const PLAYTEST_DRAFT_VERSION = 2;
export const DEFAULT_PLAYTEST_STACK_FACES: Partial<Record<PlaytestZoneId, PlaytestStackFace>> = {
  library: 'back',
  discard: 'front',
  banish: 'front',
  other: 'front',
};
export const EMPTY_OPENING_SETUP: PlaytestOpeningSetup = {
  step: 'mana',
  mulliganCount: 0,
  selectedManaInstanceIds: [],
  selectedSetupInstanceIds: [],
  handledSetupCardIds: [],
  reservedOrigins: {},
  reservedOriginOrders: {},
};

export type LegacyPlaytestCardInstance = Omit<PlaytestCardInstance, 'face'> & {
  face?: PlaytestCardFace;
};

export const cloneInstances = (instances: PlaytestCardInstance[]): PlaytestCardInstance[] =>
  normalizePileGroups(instances.map((instance) => ({ ...instance })));

export const normalizeInstanceFields = (instance: LegacyPlaytestCardInstance): PlaytestCardInstance => ({
  ...instance,
  face: instance.face ?? 'front',
});

export const orderedZoneInstances = (
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

export const renumberAllZones = (instances: PlaytestCardInstance[]): PlaytestCardInstance[] =>
  PLAYTEST_ZONES.reduce((current, zoneId) => renumberZone(current, zoneId), instances);

export const uniqueIds = (ids: string[]): string[] => [...new Set(ids)];

export const selectedOpeningIds = (state: PlaytestState): Set<string> =>
  new Set([
    ...state.openingSetup.selectedManaInstanceIds,
    ...state.openingSetup.selectedSetupInstanceIds,
  ]);

export const openingManaSetupWith = (
  setup: PlaytestOpeningSetup,
  instanceId: string,
  selected: boolean,
): PlaytestOpeningSetup => ({
  ...setup,
  step: setup.step ?? 'mana',
  mulliganCount: setup.mulliganCount ?? 0,
  selectedManaInstanceIds: selected
    ? uniqueIds([...setup.selectedManaInstanceIds, instanceId])
    : setup.selectedManaInstanceIds.filter((id) => id !== instanceId),
  selectedSetupInstanceIds: setup.selectedSetupInstanceIds,
});

export const selectedOpeningIdsFromSetup = (setup: PlaytestOpeningSetup): Set<string> =>
  new Set([
    ...setup.selectedManaInstanceIds,
    ...setup.selectedSetupInstanceIds,
  ]);

export const isManaCardInstance = (instance: PlaytestCardInstance): boolean =>
  instance.card.types.some((type) => type.key.trim().toLowerCase() === 'mana');

export const isSetupCardInstance = (instance: PlaytestCardInstance): boolean =>
  instance.card.keywords.some((keyword) => keyword.trim().toLowerCase() === 'setup');

export const setupCardIds = (instances: PlaytestCardInstance[]): Set<string> =>
  new Set(instances.filter(isSetupCardInstance).map((instance) => instance.cardId));

export const syncOpeningSelections = (state: PlaytestState): PlaytestState => {
  const instancesById = new Map(state.instances.map((instance) => [instance.instanceId, instance]));
  const ids = new Set(instancesById.keys());
  const selectedManaInstanceIds = state.openingSetup.selectedManaInstanceIds.filter((id) => ids.has(id));
  const selectedSetupInstanceIds = state.openingSetup.selectedSetupInstanceIds.filter((id) => {
    const instance = instancesById.get(id);
    return Boolean(instance?.setupOrigin && instance.zoneId === 'other');
  });
  const selectedIds = selectedOpeningIdsFromSetup({
    ...state.openingSetup,
    selectedManaInstanceIds,
    selectedSetupInstanceIds,
  });
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
      step: state.openingSetup.step ?? 'mana',
      mulliganCount: state.openingSetup.mulliganCount ?? 0,
      selectedManaInstanceIds,
      selectedSetupInstanceIds,
      handledSetupCardIds: uniqueIds(state.openingSetup.handledSetupCardIds ?? [])
        .filter((cardId) => setupCardIds(state.instances).has(cardId)),
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
): PlaytestState => ({
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

