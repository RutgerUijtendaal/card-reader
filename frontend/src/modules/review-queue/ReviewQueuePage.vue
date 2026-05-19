<template>
  <section class="page-card space-y-4">
    <h2 class="text-xl font-semibold text-slate-900">
      Review Queue
    </h2>
    <p class="text-sm text-slate-600">
      Cards below confidence threshold appear here for manual correction.
    </p>

    <ul class="grid gap-2">
      <li
        v-for="card in cards"
        :key="card.id"
        class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700"
      >
        <RouterLink
          class="font-medium text-sky-700 hover:text-sky-800"
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
import { api } from '@/api/client';
import type { PaginatedCardsResponse } from '@/modules/card-detail/types';

type ReviewCard = { id: string; name: string; confidence: number };
const cards = ref<ReviewCard[]>([]);
const nextPage = ref<number | null>(1);

const loadQueuePage = async (page: number, mode: 'replace' | 'append'): Promise<void> => {
  const response = await api.get<PaginatedCardsResponse<ReviewCard>>('/cards', {
    params: { max_confidence: 0.8, page, page_size: 100 },
  });
  cards.value = mode === 'replace' ? response.data.results : [...cards.value, ...response.data.results];
  nextPage.value = response.data.next_page;
};

const loadQueue = async (): Promise<void> => {
  await loadQueuePage(1, 'replace');
};

const loadMore = async (): Promise<void> => {
  if (nextPage.value === null) {
    return;
  }
  await loadQueuePage(nextPage.value, 'append');
};

onMounted(() => {
  void loadQueue();
});
</script>
