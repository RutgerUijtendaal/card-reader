<template>
  <section class="page-card" v-if="card">
    <h2>{{ card.name }}</h2>
    <img v-if="card.image_path" :src="toFileUrl(card.image_path)" alt="Card image" style="max-width: 320px" />
    <p><strong>Type:</strong> {{ card.type_line }}</p>
    <p><strong>Mana:</strong> {{ card.mana_cost }}</p>
    <p><strong>Confidence:</strong> {{ card.confidence }}</p>
    <p>{{ card.rules_text }}</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { api } from '@/api/client';

type CardDetail = {
  id: string;
  name: string;
  type_line: string;
  mana_cost: string;
  rules_text: string;
  confidence: number;
  image_path: string | null;
};

const route = useRoute();
const card = ref<CardDetail | null>(null);

const loadCard = async (): Promise<void> => {
  const response = await api.get<CardDetail>(`/cards/${route.params.id}`);
  card.value = response.data;
};

const toFileUrl = (path: string): string => `file:///${path.replaceAll('\\', '/')}`;

onMounted(loadCard);
</script>