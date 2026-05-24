import { computed, reactive, type Ref } from 'vue';
import type { CardListItem } from '@/modules/card-detail/types';
import { MAX_DECK_COPIES, MAX_MAINBOARD_CARD_COUNT, MIN_MAINBOARD_CARD_COUNT } from '@/modules/decks/constants';
import type { DeckCardSummary, DeckMetadataOption, DeckRecord, DeckUpsertRequest } from '@/modules/decks/types';

export type DeckForm = {
  name: string;
  description: string;
  is_public: boolean;
  hero_card_id: string;
  entries: Array<{ card_id: string; quantity: number }>;
};

export type BuilderStep = 'setup' | 'build';

type UseDeckEditorDraftOptions = {
  builderStep: Ref<BuilderStep>;
  cardLookup: Ref<Record<string, DeckCardSummary>>;
  rememberCards: (cards: CardListItem[]) => void;
};

export const useDeckEditorDraft = ({
  builderStep,
  cardLookup,
  rememberCards,
}: UseDeckEditorDraftOptions) => {
  const form = reactive<DeckForm>({
    name: '',
    description: '',
    is_public: false,
    hero_card_id: '',
    entries: [],
  });

  const isSetupStep = computed(() => builderStep.value === 'setup');
  const totalMainboardCards = computed(() => form.entries.reduce((sum, entry) => sum + entry.quantity, 0));
  const selectedHero = computed(() => (form.hero_card_id ? cardLookup.value[form.hero_card_id] ?? null : null));
  const detailedEntries = computed(() =>
    form.entries
      .map((entry) => ({
        card: cardLookup.value[entry.card_id],
        quantity: entry.quantity,
      }))
      .filter((entry): entry is { card: DeckCardSummary; quantity: number } => Boolean(entry.card)),
  );

  const deckTypeCounts = computed(() => {
    const counts = new Map<string, { type: DeckMetadataOption; count: number }>();

    const addTypes = (types: DeckMetadataOption[], quantity: number): void => {
      for (const type of types) {
        const existing = counts.get(type.id);
        if (existing) {
          existing.count += quantity;
          continue;
        }
        counts.set(type.id, { type, count: quantity });
      }
    };

    if (selectedHero.value) {
      addTypes(selectedHero.value.types, 1);
    }

    for (const entry of detailedEntries.value) {
      addTypes(entry.card.types, entry.quantity);
    }

    return [...counts.values()].sort((left, right) => {
      if (right.count !== left.count) {
        return right.count - left.count;
      }
      return left.type.label.localeCompare(right.type.label);
    });
  });

  const headerDeckTypeCounts = computed(() => deckTypeCounts.value.slice(0, 4));
  const remainingDeckTypeCount = computed(() => Math.max(deckTypeCounts.value.length - headerDeckTypeCounts.value.length, 0));

  const setupMessages = computed(() => {
    const messages: string[] = [];
    if (!form.name.trim()) messages.push('Deck name is required.');
    if (!form.hero_card_id) messages.push('A hero card is required.');
    return messages;
  });

  const validationMessages = computed(() => {
    const messages = [...setupMessages.value];
    if (totalMainboardCards.value < MIN_MAINBOARD_CARD_COUNT || totalMainboardCards.value > MAX_MAINBOARD_CARD_COUNT) {
      messages.push(`Deck must contain between ${MIN_MAINBOARD_CARD_COUNT} and ${MAX_MAINBOARD_CARD_COUNT} mainboard cards.`);
    }
    for (const entry of form.entries) {
      if (entry.quantity < 1 || entry.quantity > MAX_DECK_COPIES) {
        messages.push(`Each mainboard card quantity must stay between 1 and ${MAX_DECK_COPIES}.`);
        break;
      }
    }
    return messages;
  });

  const isDeckValid = computed(() => validationMessages.value.length === 0);
  const deckStatusLabel = computed(() => (isDeckValid.value ? 'Ready' : 'In Progress'));

  const setDeckName = (value: string): void => {
    form.name = value;
  };

  const setDeckDescription = (value: string): void => {
    form.description = value;
  };

  const setDeckPublic = (value: boolean): void => {
    form.is_public = value;
  };

  const hydrateFromDeck = (deck: DeckRecord): void => {
    form.name = deck.name;
    form.description = deck.description ?? '';
    form.is_public = deck.is_public;
    form.hero_card_id = deck.hero_card.id;
    form.entries = deck.mainboard.entries.map((entry) => ({
      card_id: entry.card.id,
      quantity: entry.quantity,
    }));

    const nextLookup = { ...cardLookup.value, [deck.hero_card.id]: deck.hero_card };
    for (const entry of deck.mainboard.entries) {
      nextLookup[entry.card.id] = entry.card;
    }
    cardLookup.value = nextLookup;
  };

  const buildPayload = (): DeckUpsertRequest => ({
    name: form.name.trim(),
    description: form.description.trim() || null,
    is_public: form.is_public,
    hero_card_id: form.hero_card_id,
    entries: form.entries.map((entry) => ({
      card_id: entry.card_id,
      quantity: entry.quantity,
    })),
  });

  const getEntryQuantity = (cardId: string): number =>
    form.entries.find((entry) => entry.card_id === cardId)?.quantity ?? 0;

  const addEntry = (card: CardListItem): void => {
    rememberCards([card]);
    const currentQuantity = getEntryQuantity(card.id);
    if (currentQuantity >= MAX_DECK_COPIES || totalMainboardCards.value >= MAX_MAINBOARD_CARD_COUNT) {
      return;
    }
    if (currentQuantity === 0) {
      form.entries.push({ card_id: card.id, quantity: 1 });
      return;
    }
    form.entries = form.entries.map((entry) =>
      entry.card_id === card.id ? { ...entry, quantity: Math.min(MAX_DECK_COPIES, entry.quantity + 1) } : entry,
    );
  };

  const removeEntry = (cardId: string): void => {
    form.entries = form.entries.filter((entry) => entry.card_id !== cardId);
  };

  const changeQuantity = (cardId: string, delta: number): void => {
    form.entries = form.entries.map((entry) =>
      entry.card_id === cardId
        ? { ...entry, quantity: Math.max(1, Math.min(MAX_DECK_COPIES, entry.quantity + delta)) }
        : entry,
    );
  };

  const setQuantity = (cardId: string, rawValue: string): void => {
    const parsed = Number.parseInt(rawValue, 10);
    const quantity = Number.isNaN(parsed) ? 1 : Math.max(1, Math.min(MAX_DECK_COPIES, parsed));
    form.entries = form.entries.map((entry) => (entry.card_id === cardId ? { ...entry, quantity } : entry));
  };

  const galleryActionLabel = (card: CardListItem): string => {
    if (isSetupStep.value) {
      return form.hero_card_id === card.id ? 'Selected Hero' : 'Use As Hero';
    }

    const quantity = getEntryQuantity(card.id);
    if (quantity === 0) return 'Add To Deck';
    if (quantity >= MAX_DECK_COPIES) return 'At Copy Limit';
    if (totalMainboardCards.value >= MAX_MAINBOARD_CARD_COUNT) return `In Deck (${quantity})`;
    return `Add Copy (${quantity}/${MAX_DECK_COPIES})`;
  };

  const galleryActionDisabled = (card: CardListItem): boolean => {
    if (isSetupStep.value) {
      return form.hero_card_id === card.id;
    }

    const quantity = getEntryQuantity(card.id);
    return quantity >= MAX_DECK_COPIES || (quantity === 0 && totalMainboardCards.value >= MAX_MAINBOARD_CARD_COUNT);
  };

  const handleGalleryAction = (card: CardListItem): void => {
    if (isSetupStep.value) {
      rememberCards([card]);
      form.hero_card_id = card.id;
      return;
    }
    addEntry(card);
  };

  return {
    form,
    isSetupStep,
    totalMainboardCards,
    selectedHero,
    detailedEntries,
    deckTypeCounts,
    headerDeckTypeCounts,
    remainingDeckTypeCount,
    setupMessages,
    validationMessages,
    isDeckValid,
    deckStatusLabel,
    setDeckName,
    setDeckDescription,
    setDeckPublic,
    hydrateFromDeck,
    buildPayload,
    changeQuantity,
    setQuantity,
    removeEntry,
    galleryActionLabel,
    galleryActionDisabled,
    handleGalleryAction,
  };
};

export type DeckEditorDraftController = ReturnType<typeof useDeckEditorDraft>;
