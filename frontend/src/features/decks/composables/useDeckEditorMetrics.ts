import { computed, type ComputedRef, type Ref } from 'vue';
import {
  getDeckBlockingMessages,
  getDeckConstraintMessages,
  getDeckWarningMessages,
  resolveDeckBuildingRules,
} from '@/domain/decks/utils/deckConstraints';
import type { DeckBuildingRules } from '@/domain/deck-building/types';
import type { DeckCardSummary, DeckMetadataOption } from '@/domain/decks/types';
import type { DeckForm, DeckFormEntry } from '@/features/decks/composables/deckEditorDraftTypes';
import { MAINBOARD_ID } from '@/features/decks/composables/useDeckEditorBoards';

type UseDeckEditorMetricsOptions = {
  form: DeckForm;
  cardLookup: Ref<Record<string, DeckCardSummary>>;
  selectedHero: ComputedRef<DeckCardSummary | null>;
  baseDeckBuildingRules: Ref<DeckBuildingRules>;
  visibleActiveBoardEntries: ComputedRef<DeckFormEntry[]>;
};

export const useDeckEditorMetrics = ({
  form,
  cardLookup,
  selectedHero,
  baseDeckBuildingRules,
  visibleActiveBoardEntries,
}: UseDeckEditorMetricsOptions) => {
  const totalMainboardCards = computed(() =>
    form.entries.reduce((sum, entry) => sum + entry.quantity, 0),
  );
  const totalSideboardCards = computed(() =>
    form.sideboards.reduce(
      (sum, sideboard) =>
        sum + sideboard.entries.reduce((boardSum, entry) => boardSum + entry.quantity, 0),
      0,
    ),
  );
  const overallTotalCards = computed(() => totalMainboardCards.value + totalSideboardCards.value);
  const overallUniqueCards = computed(() => {
    const ids = new Set(form.entries.map((entry) => entry.card_id));
    for (const sideboard of form.sideboards) {
      for (const entry of sideboard.entries) ids.add(entry.card_id);
    }
    return ids.size;
  });
  const allCardIds = computed(() => {
    const ids = new Set<string>();
    for (const entry of form.entries) ids.add(entry.card_id);
    for (const sideboard of form.sideboards) {
      for (const entry of sideboard.entries) ids.add(entry.card_id);
    }
    return [...ids].sort((left, right) => left.localeCompare(right));
  });

  const baseConstraintContext = computed(() => ({
    mainboardId: MAINBOARD_ID,
    heroCard: selectedHero.value,
    cardLookup: cardLookup.value,
    baseRules: baseDeckBuildingRules.value,
    mainboardEntries: form.entries,
    sideboards: form.sideboards,
  }));
  const deckBuildingRules = computed(() => resolveDeckBuildingRules(baseConstraintContext.value));

  const mapDetailedEntries = (entries: DeckFormEntry[]) =>
    entries
      .map((entry) => ({ card: cardLookup.value[entry.card_id], quantity: entry.quantity }))
      .filter((entry): entry is { card: DeckCardSummary; quantity: number } => Boolean(entry.card));

  const detailedMainboardEntries = computed(() => mapDetailedEntries(form.entries));
  const detailedActiveBoardEntries = computed(() => mapDetailedEntries(visibleActiveBoardEntries.value));
  const totalMainboardManaTypeCards = computed(() =>
    detailedMainboardEntries.value.reduce(
      (sum, entry) =>
        sum +
        (entry.card.types.some((type) => type.key.toLowerCase() === 'mana') ? entry.quantity : 0),
      0,
    ),
  );
  const hasFreeMulliganManaRatio = computed(
    () =>
      totalMainboardCards.value > 0 &&
      totalMainboardManaTypeCards.value / totalMainboardCards.value >= 0.25,
  );

  const deckTypeCounts = computed(() => {
    const counts = new Map<string, { type: DeckMetadataOption; count: number }>();
    const addTypes = (types: DeckMetadataOption[], quantity: number): void => {
      for (const type of types) {
        const existing = counts.get(type.id);
        if (existing) existing.count += quantity;
        else counts.set(type.id, { type, count: quantity });
      }
    };

    if (selectedHero.value) addTypes(selectedHero.value.types, 1);
    const sideboardEntries = form.sideboards.flatMap((sideboard) =>
      mapDetailedEntries(sideboard.entries),
    );
    for (const entry of [...detailedMainboardEntries.value, ...sideboardEntries]) {
      addTypes(entry.card.types, entry.quantity);
    }
    return [...counts.values()].sort(
      (left, right) => right.count - left.count || left.type.label.localeCompare(right.type.label),
    );
  });

  const headerDeckTypeCounts = computed(() => deckTypeCounts.value.slice(0, 4));
  const remainingDeckTypeCount = computed(() =>
    Math.max(deckTypeCounts.value.length - headerDeckTypeCounts.value.length, 0),
  );
  const setupMessages = computed<string[]>(() => []);
  const validationMessages = computed(() => {
    const messages = [...setupMessages.value];
    if (form.sideboards.some((sideboard) => !sideboard.name.trim())) {
      messages.push('Each sideboard needs a name.');
    }
    messages.push(...getDeckConstraintMessages(baseConstraintContext.value));
    return messages;
  });
  const warningMessages = computed(() => getDeckWarningMessages(baseConstraintContext.value));
  const blockingMessages = computed(() => getDeckBlockingMessages(baseConstraintContext.value));
  const isDeckValid = computed(() => validationMessages.value.length === 0);
  const deckStatusLabel = computed(() => (isDeckValid.value ? 'Ready' : 'In Progress'));

  return {
    totalMainboardCards,
    totalSideboardCards,
    overallTotalCards,
    overallUniqueCards,
    allCardIds,
    baseConstraintContext,
    deckBuildingRules,
    detailedMainboardEntries,
    detailedActiveBoardEntries,
    totalMainboardManaTypeCards,
    hasFreeMulliganManaRatio,
    deckTypeCounts,
    headerDeckTypeCounts,
    remainingDeckTypeCount,
    setupMessages,
    validationMessages,
    warningMessages,
    blockingMessages,
    isDeckValid,
    deckStatusLabel,
  };
};
