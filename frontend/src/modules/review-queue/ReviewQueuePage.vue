<template>
  <section class="page-card space-y-4">
    <h2 class="theme-section-title text-xl font-semibold">
      Review Queue
    </h2>
    <p class="theme-section-muted text-sm">
      Cards below confidence threshold appear here for manual correction.
    </p>

    <ul class="grid gap-2">
      <li
        v-for="card in cards"
        :key="card.id"
        class="theme-card-frame theme-section-title rounded-lg px-3 py-2 text-sm"
      >
        <RouterLink
          class="theme-link font-medium"
          :to="`/cards/${card.id}/edit`"
        >
          {{ card.name }}
        </RouterLink>
        - {{ card.confidence }}
      </li>
    </ul>
    <button
      v-if="nextPage !== null"
      class="btn-secondary"
      type="button"
      @click="loadMore"
    >
      Load more
    </button>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useCardCollection } from '@/modules/card-search/useCardCollection';

type ReviewCard = { id: string; name: string; confidence: number };
const filtersLoaded = ref(true);
const collection = useCardCollection<ReviewCard>({
  buildSearchParams: () => {
    const params = new URLSearchParams();
    params.set('max_confidence', '0.8');
    return params;
  },
  filtersLoaded,
  pageSize: 100,
});
const cards = collection.cards;
const nextPage = collection.nextPage;

const loadMore = async (): Promise<void> => {
  await collection.loadNextPage();
};

onMounted(() => {
  void collection.searchCards();
});
</script>
