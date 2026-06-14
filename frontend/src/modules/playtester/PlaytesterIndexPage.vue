<template>
  <section class="flex flex-col gap-6">
    <AppPageHeader
      :icon="Gamepad2"
      title="Playtester"
      subtitle="Choose a deck and run opening hands, setup, and early turns."
      title-tag="h2"
      title-class="text-xl"
    />

    <section class="mx-auto mt-4 flex w-full max-w-6xl flex-col gap-5 px-1">
      <div class="theme-divider flex flex-col gap-3 border-b pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div class="min-w-0">
          <h3 class="theme-section-title text-sm font-semibold">
            Select Deck
          </h3>
          <p class="theme-section-muted mt-1 text-sm">
            Start a manual playtest from one of your decks or a public deck.
          </p>
        </div>
        <div class="relative w-full sm:max-w-md">
          <Search class="theme-section-muted pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" />
          <input
            v-model="searchQuery"
            class="input-base h-10 w-full pl-10 pr-3 text-sm"
            placeholder="Search by deck, hero, owner, or card"
          >
        </div>
      </div>

      <div
        v-if="loading"
        class="playtester-deck-grid grid gap-4"
      >
        <DeckLoadingSkeleton
          v-for="index in 4"
          :key="`playtester-loading-${index}`"
        />
      </div>

      <div
        v-else-if="filteredSuggestions.length === 0"
        class="theme-empty-state text-sm"
      >
        No decks match the current search.
      </div>

      <div
        v-else
        class="space-y-6"
      >
        <section
          v-if="ownedSuggestions.length > 0"
          class="space-y-3"
        >
          <div class="flex items-center justify-between gap-3">
            <h3 class="theme-section-title text-sm font-semibold">
              Your Decks
            </h3>
            <span class="theme-pill theme-pill-neutral text-xs">{{ ownedSuggestions.length }}</span>
          </div>
          <div class="playtester-deck-grid grid gap-4">
            <DeckListCard
              v-for="suggestion in ownedSuggestions"
              :key="`owned-${suggestion.deck.id}`"
              :deck="suggestion.deck"
              mode="owned"
              :title-to="`/playtester/${suggestion.deck.id}`"
            >
              <template #actions>
                <RouterLink
                  class="btn-primary whitespace-nowrap"
                  :to="`/playtester/${suggestion.deck.id}`"
                >
                  Start Playtest
                </RouterLink>
              </template>
            </DeckListCard>
          </div>
        </section>

        <section
          v-if="publicSuggestions.length > 0"
          class="space-y-3"
        >
          <div class="flex items-center justify-between gap-3">
            <h3 class="theme-section-title text-sm font-semibold">
              Public Decks
            </h3>
            <span class="theme-pill theme-pill-neutral text-xs">{{ publicSuggestions.length }}</span>
          </div>
          <div class="playtester-deck-grid grid gap-4">
            <DeckListCard
              v-for="suggestion in publicSuggestions"
              :key="`public-${suggestion.deck.id}`"
              :deck="suggestion.deck"
              mode="browse"
              :title-to="`/playtester/${suggestion.deck.id}`"
            >
              <template #actions>
                <RouterLink
                  class="btn-primary whitespace-nowrap"
                  :to="`/playtester/${suggestion.deck.id}`"
                >
                  Start Playtest
                </RouterLink>
              </template>
            </DeckListCard>
          </div>
        </section>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { Gamepad2, Search } from 'lucide-vue-next';
import { RouterLink } from 'vue-router';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import DeckListCard from '@/components/decks/DeckListCard.vue';
import DeckLoadingSkeleton from '@/components/decks/DeckLoadingSkeleton.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import { fetchMyDecks, fetchPublicDecks } from '@/modules/decks/api';
import type { DeckRecord } from '@/modules/decks/types';
import type { PlaytestDeckSuggestion } from '@/modules/playtester/types';

const auth = useAuthStore();
const loading = ref(true);
const searchQuery = ref('');
const suggestions = ref<PlaytestDeckSuggestion[]>([]);

const cardNamesForDeck = (deck: DeckRecord): string =>
  [
    ...deck.mainboard.entries.map((entry) => entry.card.name),
    ...deck.sideboards.flatMap((sideboard) => sideboard.entries.map((entry) => entry.card.name)),
  ].join(' ');

const suggestionMatches = (suggestion: PlaytestDeckSuggestion, query: string): boolean => {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return true;
  }
  const deck = suggestion.deck;
  return [
    deck.name,
    deck.hero_card.name,
    deck.owner.username,
    cardNamesForDeck(deck),
  ].some((value) => value.toLowerCase().includes(normalizedQuery));
};

const filteredSuggestions = computed(() =>
  suggestions.value.filter((suggestion) => suggestionMatches(suggestion, searchQuery.value)),
);
const ownedSuggestions = computed(() =>
  filteredSuggestions.value.filter((suggestion) => suggestion.source === 'owned').slice(0, 6),
);
const publicSuggestions = computed(() => {
  const ownedDeckIds = new Set(ownedSuggestions.value.map((suggestion) => suggestion.deck.id));
  return filteredSuggestions.value
    .filter((suggestion) => suggestion.source === 'public' && !ownedDeckIds.has(suggestion.deck.id))
    .slice(0, 8);
});

const loadSuggestions = async (): Promise<void> => {
  loading.value = true;
  try {
    const [ownedDecks, publicDecks] = await Promise.all([
      auth.authenticated || !auth.authEnabled ? fetchMyDecks() : Promise.resolve<DeckRecord[]>([]),
      fetchPublicDecks(),
    ]);
    suggestions.value = [
      ...ownedDecks.map((deck) => ({ deck, source: 'owned' as const })),
      ...publicDecks.map((deck) => ({ deck, source: 'public' as const })),
    ];
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  void loadSuggestions();
});
</script>

<style scoped>
.playtester-deck-grid {
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 44rem), 1fr));
}
</style>
