<template>
  <section class="space-y-5">
    <div class="page-card flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div>
        <h2 class="theme-section-title text-xl font-semibold">
          {{ deckId ? 'Edit Deck' : 'Create Deck' }}
        </h2>
        <p class="theme-section-muted text-sm">
          Build a valid deck with exactly one hero and sixty non-hero mainboard cards.
        </p>
      </div>

      <div class="flex flex-wrap gap-2">
        <RouterLink
          class="btn-secondary"
          to="/my/decks"
        >
          Back to My Decks
        </RouterLink>
        <button
          class="btn-primary"
          type="button"
          :disabled="saving || validationMessages.length > 0"
          @click="saveDeck"
        >
          {{ saving ? 'Saving...' : deckId ? 'Save Deck' : 'Create Deck' }}
        </button>
      </div>
    </div>

    <div
      v-if="loading"
      class="page-card theme-section-muted text-sm"
    >
      Loading deck...
    </div>

    <div
      v-else
      class="grid gap-5 xl:grid-cols-[320px_320px_minmax(0,1fr)]"
    >
      <aside class="page-card space-y-4">
        <label class="field-label">
          Name
          <input
            v-model="form.name"
            class="input-base"
            placeholder="Deck name"
          >
        </label>

        <label class="field-label">
          Description
          <textarea
            v-model="form.description"
            class="input-base min-h-28"
            placeholder="Optional description"
          />
        </label>

        <label class="theme-section-title flex items-center gap-3 text-sm font-semibold">
          <input
            v-model="form.is_public"
            type="checkbox"
            class="theme-checkbox h-4 w-4"
          >
          <span>Public deck</span>
        </label>

        <div
          v-if="validationMessages.length > 0"
          class="theme-muted-panel space-y-2 p-3"
        >
          <p class="theme-section-title text-sm font-semibold">
            Validation
          </p>
          <p
            v-for="message in validationMessages"
            :key="message"
            class="theme-error-text text-sm"
          >
            {{ message }}
          </p>
        </div>
      </aside>

      <section class="page-card flex min-h-0 flex-col space-y-4">
        <div>
          <h3 class="theme-section-title text-base font-semibold">
            Hero
          </h3>
          <p class="theme-section-muted text-sm">
            Search and pick exactly one hero card.
          </p>
        </div>

        <input
          v-model="heroQuery"
          class="input-base"
          placeholder="Search hero cards..."
          @keydown.enter.prevent
        >

        <div
          v-if="selectedHero"
          class="theme-card-frame flex items-center gap-3 rounded-xl p-3"
        >
          <div class="min-w-0 flex-1">
            <p class="theme-section-title text-sm font-semibold">
              {{ selectedHero.name }}
            </p>
            <p class="theme-section-muted text-xs">
              {{ selectedHero.label }}
            </p>
          </div>
          <button
            class="btn-danger-secondary px-2 py-1 text-xs"
            type="button"
            @click="form.hero_card_id = ''"
          >
            Remove
          </button>
        </div>

        <div class="app-scrollbar min-h-0 flex-1 space-y-2 overflow-y-auto pr-1 xl:max-h-[28rem]">
          <button
            v-for="card in heroResults"
            :key="card.id"
            type="button"
            class="theme-selected-surface flex w-full items-center justify-between rounded-xl px-3 py-2 text-left transition hover:-translate-y-0.5"
            :disabled="form.hero_card_id === card.id"
            @click="form.hero_card_id = card.id"
          >
            <div>
              <p class="theme-section-title text-sm font-medium">
                {{ card.name }}
              </p>
              <p class="theme-section-muted text-xs">
                {{ card.label }}
              </p>
            </div>
            <span class="theme-link text-xs font-semibold">
              {{ form.hero_card_id === card.id ? 'Selected' : 'Select' }}
            </span>
          </button>
        </div>
      </section>

      <section class="page-card flex min-h-0 flex-col space-y-4">
        <div>
          <h3 class="theme-section-title text-base font-semibold">
            Mainboard
          </h3>
          <p class="theme-section-muted text-sm">
            Add non-hero cards and adjust quantities up to four copies each.
          </p>
        </div>

        <input
          v-model="mainboardQuery"
          class="input-base"
          placeholder="Search mainboard cards..."
          @keydown.enter.prevent
        >

        <div class="theme-muted-panel p-3">
          <p class="theme-section-title text-sm font-semibold">
            {{ totalMainboardCards }} / 60 cards
          </p>
          <p class="theme-section-muted text-xs">
            {{ form.entries.length }} unique cards
          </p>
        </div>

        <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div class="app-scrollbar min-h-0 space-y-2 overflow-y-auto pr-1 xl:max-h-[30rem]">
            <button
              v-for="card in mainboardResults"
              :key="card.id"
              type="button"
              class="theme-selected-surface flex w-full items-center justify-between rounded-xl px-3 py-2 text-left transition hover:-translate-y-0.5"
              :disabled="entryIds.has(card.id)"
              @click="addEntry(card.id)"
            >
              <div>
                <p class="theme-section-title text-sm font-medium">
                  {{ card.name }}
                </p>
                <p class="theme-section-muted text-xs">
                  {{ card.label }}
                </p>
              </div>
              <span class="theme-link text-xs font-semibold">
                {{ entryIds.has(card.id) ? 'Added' : 'Add' }}
              </span>
            </button>
          </div>

          <div class="app-scrollbar min-h-0 space-y-2 overflow-y-auto pr-1 xl:max-h-[30rem]">
            <div
              v-if="form.entries.length === 0"
              class="theme-empty-state"
            >
              No mainboard cards selected yet.
            </div>
            <div
              v-for="entry in detailedEntries"
              :key="entry.card.id"
              class="theme-card-frame flex items-center gap-3 rounded-xl p-3"
            >
              <div class="min-w-0 flex-1">
                <p class="theme-section-title text-sm font-semibold">
                  {{ entry.card.name }}
                </p>
                <p class="theme-section-muted text-xs">
                  {{ entry.card.label }}
                </p>
              </div>

              <div class="flex items-center gap-2">
                <button
                  class="btn-secondary h-8 w-8 px-0"
                  type="button"
                  @click="changeQuantity(entry.card.id, -1)"
                >
                  -
                </button>
                <input
                  :value="entry.quantity"
                  class="input-base w-14 px-2 text-center"
                  type="number"
                  min="1"
                  max="4"
                  @input="setQuantity(entry.card.id, ($event.target as HTMLInputElement).value)"
                >
                <button
                  class="btn-secondary h-8 w-8 px-0"
                  type="button"
                  @click="changeQuantity(entry.card.id, 1)"
                >
                  +
                </button>
                <button
                  class="btn-danger-secondary px-2 py-1 text-xs"
                  type="button"
                  @click="removeEntry(entry.card.id)"
                >
                  Remove
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useDebounceFn } from '@vueuse/core';
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { useRoute, useRouter } from 'vue-router';
import { api } from '@/api/client';
import { createDeck, fetchMyDeck, updateDeck } from '@/modules/decks/api';
import type { DeckCardSummary, DeckRecord, DeckUpsertRequest } from '@/modules/decks/types';
import type { CardListItem, PaginatedCardsResponse } from '@/modules/card-detail/types';

type DeckForm = {
  name: string;
  description: string;
  is_public: boolean;
  hero_card_id: string;
  entries: Array<{ card_id: string; quantity: number }>;
};

const route = useRoute();
const router = useRouter();

const deckId = computed(() => (typeof route.params.id === 'string' ? route.params.id : ''));
const loading = ref(false);
const saving = ref(false);
const heroQuery = ref('');
const mainboardQuery = ref('');
const heroResults = ref<CardListItem[]>([]);
const mainboardResults = ref<CardListItem[]>([]);
const cardLookup = ref<Record<string, DeckCardSummary>>({});

const form = reactive<DeckForm>({
  name: '',
  description: '',
  is_public: false,
  hero_card_id: '',
  entries: [],
});

const entryIds = computed(() => new Set(form.entries.map((entry) => entry.card_id)));
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

const validationMessages = computed(() => {
  const messages: string[] = [];
  if (!form.name.trim()) messages.push('Deck name is required.');
  if (!form.hero_card_id) messages.push('A hero card is required.');
  if (totalMainboardCards.value !== 60) messages.push('Deck must contain exactly 60 mainboard cards.');
  for (const entry of form.entries) {
    if (entry.quantity < 1 || entry.quantity > 4) {
      messages.push('Each mainboard card quantity must stay between 1 and 4.');
      break;
    }
  }
  return messages;
});

const rememberCards = (cards: CardListItem[]): void => {
  const nextLookup = { ...cardLookup.value };
  for (const card of cards) {
    nextLookup[card.id] = {
      id: card.id,
      key: card.key,
      label: card.label,
      name: card.name,
      is_hero: card.is_hero,
      image_url: card.image_url,
    };
  }
  cardLookup.value = nextLookup;
};

const fetchPickerCards = async (query: string, isHero: boolean): Promise<CardListItem[]> => {
  const response = await api.get<PaginatedCardsResponse<CardListItem>>('/cards', {
    params: {
      q: query || undefined,
      is_hero: isHero,
      page_size: 20,
    },
  });
  rememberCards(response.data.results);
  return response.data.results;
};

const loadHeroResults = useDebounceFn(async () => {
  heroResults.value = await fetchPickerCards(heroQuery.value, true);
}, 200);

const loadMainboardResults = useDebounceFn(async () => {
  mainboardResults.value = await fetchPickerCards(mainboardQuery.value, false);
}, 200);

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

const loadDeck = async (): Promise<void> => {
  if (!deckId.value) return;
  loading.value = true;
  try {
    const deck = await fetchMyDeck(deckId.value);
    hydrateFromDeck(deck);
  } finally {
    loading.value = false;
  }
};

const addEntry = (cardId: string): void => {
  if (entryIds.value.has(cardId)) return;
  form.entries.push({ card_id: cardId, quantity: 1 });
};

const removeEntry = (cardId: string): void => {
  form.entries = form.entries.filter((entry) => entry.card_id !== cardId);
};

const changeQuantity = (cardId: string, delta: number): void => {
  form.entries = form.entries.map((entry) =>
    entry.card_id === cardId
      ? { ...entry, quantity: Math.max(1, Math.min(4, entry.quantity + delta)) }
      : entry,
  );
};

const setQuantity = (cardId: string, rawValue: string): void => {
  const parsed = Number.parseInt(rawValue, 10);
  const quantity = Number.isNaN(parsed) ? 1 : Math.max(1, Math.min(4, parsed));
  form.entries = form.entries.map((entry) => (entry.card_id === cardId ? { ...entry, quantity } : entry));
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

const saveDeck = async (): Promise<void> => {
  if (validationMessages.value.length > 0) {
    toast.error(validationMessages.value[0]);
    return;
  }
  saving.value = true;
  try {
    const payload = buildPayload();
    if (deckId.value) {
      await updateDeck(deckId.value, payload);
      toast.success('Deck updated.');
      await router.push(`/my/decks/${deckId.value}/edit`);
      return;
    }
    const created = await createDeck(payload);
    toast.success('Deck created.');
    await router.push(`/my/decks/${created.id}/edit`);
  } finally {
    saving.value = false;
  }
};

watch(heroQuery, () => {
  void loadHeroResults();
}, { immediate: true });

watch(mainboardQuery, () => {
  void loadMainboardResults();
}, { immediate: true });

onMounted(async () => {
  await Promise.all([loadDeck(), loadHeroResults(), loadMainboardResults()]);
});
</script>
