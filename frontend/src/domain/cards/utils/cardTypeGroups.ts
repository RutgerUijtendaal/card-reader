import {
  buildTypeSortBuckets,
  isManaTypeKey,
  normalizeTypeKey,
  type CardTypeMetadata,
  type TypeSortMetadata,
} from '@/domain/cards/utils/gallery/cardSort';

type CardTypeGroupCardLike = {
  id?: string;
  label?: string;
  name?: string;
  types?: Array<Pick<CardTypeMetadata, 'key'> & Partial<Pick<CardTypeMetadata, 'label'>>>;
};

export type CardTypeGroup<TEntry> = {
  key: string;
  label: string;
  entries: TEntry[];
};

type CardTypeGroupOptions<TEntry> = {
  compareEntries?: (left: TEntry, right: TEntry) => number;
};

const UNTYPED_GROUP_KEY = 'untyped';
const UNTYPED_GROUP_LABEL = 'Untyped';

const compareEntriesByCardIdentity = <TEntry extends { card: CardTypeGroupCardLike }>(
  left: TEntry,
  right: TEntry,
): number =>
  (left.card.name ?? '').localeCompare(right.card.name ?? '')
  || (left.card.label ?? '').localeCompare(right.card.label ?? '')
  || (left.card.id ?? '').localeCompare(right.card.id ?? '');

const hasEntries = <TEntry>(group: CardTypeGroup<TEntry> | undefined): group is CardTypeGroup<TEntry> =>
  group !== undefined && group.entries.length > 0;

const includeEntryTypes = <TEntry extends { card: CardTypeGroupCardLike }>(
  types: TypeSortMetadata[],
  entries: TEntry[],
): TypeSortMetadata[] => {
  const mergedTypes = [...types];
  const knownTypeKeys = new Set(types.map((type) => normalizeTypeKey(type.key)));
  for (const entry of entries) {
    for (const type of entry.card.types ?? []) {
      const normalizedKey = normalizeTypeKey(type.key);
      if (!normalizedKey || knownTypeKeys.has(normalizedKey)) {
        continue;
      }
      knownTypeKeys.add(normalizedKey);
      mergedTypes.push({
        key: type.key,
        label: type.label?.trim() || type.key,
        linked_card_count: 0,
      });
    }
  }
  return mergedTypes;
};

export const groupCardEntriesByType = <TEntry extends { card: CardTypeGroupCardLike }>(
  entries: TEntry[],
  types: TypeSortMetadata[],
  options: CardTypeGroupOptions<TEntry> = {},
): CardTypeGroup<TEntry>[] => {
  const compareEntries = options.compareEntries ?? compareEntriesByCardIdentity;
  const orderedTypeBuckets = buildTypeSortBuckets(includeEntryTypes(types, entries));
  const groups = new Map<string, CardTypeGroup<TEntry>>(
    orderedTypeBuckets.map((type) => [
      type.normalizedKey,
      {
        key: type.key,
        label: type.label,
        entries: [],
      },
    ]),
  );
  const untypedGroup: CardTypeGroup<TEntry> = {
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
