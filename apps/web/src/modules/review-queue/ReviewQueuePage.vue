<template>
  <section class="page-card">
    <h2>Review Queue</h2>
    <p>Cards below confidence threshold appear here for manual correction.</p>
    <ul>
      <li v-for="card in cards" :key="card.id">
        <RouterLink :to="`/cards/${card.id}`">{{ card.name }}</RouterLink> - {{ card.confidence }}
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