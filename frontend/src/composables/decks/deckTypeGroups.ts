import {
  buildTypeSortBuckets,
  isManaTypeKey,
  normalizeTypeKey,
  type CardTypeMetadata,
  type TypeSortMetadata,
} from '@/composables/card-gallery/cardSort';

type DeckTypeGroupCardLike = {
  id: string;
  label: string;
  name: string;
  types?: CardTypeMetadata[];
};

export type DeckTypeGroup<TEntry> = {
  key: string;
  label: string;
  entries: TEntry[];
};

type DeckTypeGroupOptions<TEntry> = {
  compareEntries?: (left: TEntry, right: TEntry) => number;
};

const UNTYPED_GROUP_KEY = 'untyped';
const UNTYPED_GROUP_LABEL = 'Untyped';

const compareEntriesByCardIdentity = <TEntry extends { card: DeckTypeGroupCardLike }>(
  left: TEntry,
  right: TEntry,
): number =>
  left.card.name.localeCompare(right.card.name)
  || left.card.label.localeCompare(right.card.label)
  || left.card.id.localeCompare(right.card.id);

const hasEntries = <TEntry>(group: DeckTypeGroup<TEntry> | undefined): group is DeckTypeGroup<TEntry> =>
  group !== undefined && group.entries.length > 0;

export const groupDeckEntriesByType = <TEntry extends { card: DeckTypeGroupCardLike }>(
  entries: TEntry[],
  types: TypeSortMetadata[],
  options: DeckTypeGroupOptions<TEntry> = {},
): DeckTypeGroup<TEntry>[] => {
  const compareEntries = options.compareEntries ?? compareEntriesByCardIdentity;
  const orderedTypeBuckets = buildTypeSortBuckets(types);
  const groups = new Map<string, DeckTypeGroup<TEntry>>(
    orderedTypeBuckets.map((type) => [
      type.normalizedKey,
      {
        key: type.key,
        label: type.label,
        entries: [],
      },
    ]),
  );
  const untypedGroup: DeckTypeGroup<TEntry> = {
    key: UNTYPED_GROUP_KEY,
    label: UNTYPED_GROUP_LABEL,
    entries: [],
  };

  for (const entry of entries) {
    const entryTypeKeys = new Set((entry.card.types ?? []).map((type) => normalizeTypeKey(type.key)));
    const matchedBucket = orderedTypeBuckets.find((type) => entryTypeKeys.has(type.normalizedKey));
    if (!matchedBucket) {
      untypedGroup.entries.push(entry);
      continue;
    }
    groups.get(matchedBucket.normalizedKey)?.entries.push(entry);
  }

  const nonManaGroups = orderedTypeBuckets
    .filter((type) => !isManaTypeKey(type.normalizedKey))
    .map((type) => groups.get(type.normalizedKey))
    .filter(hasEntries);
  const manaGroups = orderedTypeBuckets
    .filter((type) => isManaTypeKey(type.normalizedKey))
    .map((type) => groups.get(type.normalizedKey))
    .filter(hasEntries);

  const nonEmptyGroups = [
    ...nonManaGroups,
    ...(untypedGroup.entries.length > 0 ? [untypedGroup] : []),
    ...manaGroups,
  ];

  return nonEmptyGroups.map((group) => ({
    ...group,
    entries: [...group.entries].sort(compareEntries),
  }));
};
