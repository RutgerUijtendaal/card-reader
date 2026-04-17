<template>
  <section v-if="card" class="page-card space-y-4">
    <h2 class="text-xl font-semibold text-slate-900">{{ card.name }}</h2>

    <img
      v-if="card.image_url"
      :src="toAbsoluteApiUrl(card.image_url)"
      alt="Card image"
      class="max-h-[560px] w-full max-w-xs rounded-lg border border-slate-200 object-contain"
    />

    <p class="text-sm text-slate-700"><span class="font-semibold">Type:</span> {{ card.type_line }}</p>
    <p class="text-sm text-slate-700"><span class="font-semibold">Mana:</span> {{ card.mana_cost }}</p>
    <p class="text-sm text-slate-700"><span class="font-semibold">Confidence:</span> {{ card.confidence }}</p>
    <p class="text-base text-slate-800">{{ card.rules_text }}</p>
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
  image_url: string | null;
};

const route = useRoute();
const card = ref<CardDetail | null>(null);

const loadCard = async (): Promise<void> => {
  const response = await api.get<CardDetail>(`/cards/${route.params.id}`);
  card.value = response.data;
};

const toAbsoluteApiUrl = (urlPath: string): string => {
  const base = api.defaults.baseURL ?? 'http://127.0.0.1:8000';
  if (urlPath.startsWith('http://') || urlPath.startsWith('https://')) {
    return urlPath;
  }
  return `${base.replace(/\/$/, '')}/${urlPath.replace(/^\//, '')}`;
};

onMounted(loadCard);
</script>
