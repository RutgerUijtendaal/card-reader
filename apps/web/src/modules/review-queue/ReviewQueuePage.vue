<template>
  <section class="page-card space-y-4">
    <h2 class="text-xl font-semibold text-slate-900">Review Queue</h2>
    <p class="text-sm text-slate-600">Cards below confidence threshold appear here for manual correction.</p>

    <ul class="grid gap-2">
      <li
        v-for="card in cards"
        :key="card.id"
        class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700"
      >
        <RouterLink class="font-medium text-sky-700 hover:text-sky-800" :to="`/cards/${card.id}`">{{ card.name }}</RouterLink>
        - {{ card.confidence }}
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '@/api/client';

type ReviewCard = { id: string; name: string; confidence: number };
const cards = ref<ReviewCard[]>([]);

const loadQueue = async (): Promise<void> => {
  const response = await api.get<ReviewCard[]>('/cards', { params: { max_confidence: 0.8 } });
  cards.value = response.data;
};

onMounted(loadQueue);
</script>