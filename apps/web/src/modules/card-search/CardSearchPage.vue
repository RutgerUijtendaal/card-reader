<template>
  <section class="page-card space-y-4">
    <h2 class="text-xl font-semibold text-slate-900">Card Search</h2>
    <form class="flex flex-col gap-2 sm:flex-row" @submit.prevent="searchCards">
      <input v-model="query" class="input-base" placeholder="Search card text" />
      <button class="btn-primary" type="submit">Search</button>
    </form>

    <ul class="grid gap-2">
      <li
        v-for="card in cards"
        :key="card.id"
        class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700"
      >
        <RouterLink class="font-medium text-sky-700 hover:text-sky-800" :to="`/cards/${card.id}`">
          {{ card.name }} ({{ card.template_id }})
        </RouterLink>
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