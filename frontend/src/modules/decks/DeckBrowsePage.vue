<template>
  <section class="flex h-[calc(100vh-3rem)] min-h-0 flex-col gap-5 overflow-hidden">
    <AppPageHeader
      :icon="BookOpen"
      title="Decks"
      subtitle="Browse public decks and inspect their hero, mainboard, and sideboards."
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <RouterLink
          v-if="auth.authenticated"
          class="btn-secondary"
          to="/my/decks"
        >
          My Decks
        </RouterLink>
        <RouterLink
          v-if="auth.authenticated"
          class="btn-primary"
          to="/my/decks/new"
        >
          New Deck
        </RouterLink>
      </template>
    </AppPageHeader>

    <section class="grid min-h-0 flex-1 gap-6 overflow-hidden xl:grid-cols-[23rem_minmax(0,1fr)]">
      <DeckBrowseFiltersPanel
        :controller="filterController"
        :total-count="decks.length"
      />

      <div class="app-scrollbar min-h-0 overflow-y-auto pr-1">
        <div
          v-if="loading || !filtersLoaded"
          class="page-card theme-section-muted text-sm"
        >
          Loading decks...
        </div>

        <div
          v-else-if="decks.length === 0"
          class="page-card theme-section-muted text-sm"
        >
          {{ hasActiveFilters ? 'No public decks match the current filters.' : 'No public decks yet.' }}
        </div>

        <div
          v-else
          class="grid gap-4 px-1 pb-3 pt-2 lg:grid-cols-2"
        >
          <DeckListCard
            v-for="deck in decks"
            :key="deck.id"
            :deck="deck"
            mode="browse"
            :title-to="`/decks/${deck.id}`"
          />
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { useDebounceFn } from '@vueuse/core';
import { computed, onMounted, ref, watch } from 'vue';
import { BookOpen } from 'lucide-vue-next';
import { useRoute, useRouter } from 'vue-router';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import { fetchPublicDecks } from '@/modules/decks/api';
import DeckBrowseFiltersPanel from '@/modules/decks/components/DeckBrowseFiltersPanel.vue';
import { useDeckBrowseFilters } from '@/modules/decks/composables/useDeckBrowseFilters';
import {
  buildDeckBrowseFilterApiSearchParams,
  buildDeckBrowseFilterRouteQuery,
  getDeckBrowseFilterSignature,
  parseDeckBrowseFilterRouteQuery,
  sameDeckBrowseFilterState,
} from '@/modules/decks/deckBrowseFilterState';
import DeckListCard from '@/modules/decks/components/DeckListCard.vue';
import type { DeckRecord } from '@/modules/decks/types';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const decks = ref<DeckRecord[]>([]);
const loading = ref(false);
const filterController = useDeckBrowseFilters();
const { filtersLoaded, selectionState, readFilterState, applyRouteFilterState, loadFilters } = filterController;
const currentRouteFilterState = computed(() => parseDeckBrowseFilterRouteQuery(route.query));
const currentRouteSignature = computed(() => getDeckBrowseFilterSignature(currentRouteFilterState.value));
const hasActiveFilters = computed(() => currentRouteSignature.value.length > 0);

const loadDecks = async (): Promise<void> => {
  loading.value = true;
  try {
    decks.value = await fetchPublicDecks(buildDeckBrowseFilterApiSearchParams(selectionState.value));
  } finally {
    loading.value = false;
  }
};

const debouncedUpdateRoute = useDebounceFn(() => {
  if (!filtersLoaded.value) {
    return;
  }
  const nextRouteState = readFilterState();
  if (sameDeckBrowseFilterState(nextRouteState, currentRouteFilterState.value)) {
    return;
  }
  void router.replace({
    path: '/decks',
    query: buildDeckBrowseFilterRouteQuery(nextRouteState),
  });
}, 250);

watch(
  selectionState,
  () => {
    debouncedUpdateRoute();
  },
  { deep: true },
);

watch(
  [currentRouteSignature, filtersLoaded],
  async ([, ready]) => {
    if (!ready) {
      return;
    }
    const routeState = currentRouteFilterState.value;
    if (!sameDeckBrowseFilterState(readFilterState(), routeState)) {
      applyRouteFilterState(routeState);
    }
    await loadDecks();
  },
  { immediate: true },
);

onMounted(() => {
  void loadFilters().catch(() => undefined);
});
</script>
