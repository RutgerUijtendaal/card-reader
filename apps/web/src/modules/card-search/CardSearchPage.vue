<template>
  <section class="page-card">
    <h2>Card Search</h2>
    <form @submit.prevent="searchCards">
      <input v-model="query" placeholder="Search card text" />
      <button type="submit">Search</button>
    </form>
    <ul>
      <li v-for="card in cards" :key="card.id">
        <RouterLink :to="`/cards/${card.id}`">{{ card.name }} ({{ card.template_id }})</RouterLink>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { api } from '@/api/client';

type CardListItem = {
  id: string;
  name: string;
  template_id: string;
};

const query = ref('');
const cards = ref<CardListItem[]>([]);

const searchCards = async (): Promise<void> => {
  const response = await api.get<CardListItem[]>('/cards', { params: { q: query.value } });
  cards.value = response.data;
};
</script>