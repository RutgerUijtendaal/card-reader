<template>
  <section class="space-y-4">
    <AppPageHeader
      :icon="ClipboardCheck"
      title="Review Queue"
      subtitle="Cards below confidence threshold appear here for manual correction."
      title-tag="h2"
      title-class="text-xl"
    >
      <template #bottomRight>
        <div class="theme-section-muted text-sm font-medium">
          {{ cards.length }} loaded
        </div>
        <button
          v-if="nextPage !== null"
          class="btn-secondary"
          type="button"
          @click="loadMore"
        >
          Load more
        </button>
      </template>
    </AppPageHeader>

    <div class="page-card">
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
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { ClipboardCheck } from 'lucide-vue-next';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import { useCardCollection } from '@/composables/useCardCollection';

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
