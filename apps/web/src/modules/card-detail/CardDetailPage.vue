<template>
  <section class="space-y-5">
    <div class="flex items-center justify-between gap-3">
      <button class="btn-secondary inline-flex items-center gap-2" type="button" @click="goBack">
        <ArrowLeft class="h-4 w-4" />
        <span>Back to Gallery</span>
      </button>
      <div v-if="card" class="text-right">
        <h2 class="text-xl font-semibold text-slate-900">{{ card.name }}</h2>
        <p class="text-xs text-slate-500">{{ versions.length }} versions</p>
      </div>
    </div>

    <div class="flex flex-wrap items-start gap-5">
      <CardVersionGalleryItem
        v-for="version in versions"
        :key="version.id"
        :version="version"
        :symbol-by-key="symbolByKey"
      />
    </div>

    <div v-if="versions.length === 0" class="page-card text-sm text-slate-500">No versions found.</div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ArrowLeft } from 'lucide-vue-next';
import { api } from '@/api/client';
import CardVersionGalleryItem, { type CardVersionGalleryItemModel } from '@/components/cards/CardVersionGalleryItem.vue';

type MetadataOption = {
  id: string;
  key: string;
  label: string;
};

type SymbolFilterOption = MetadataOption & {
  text_token: string;
  asset_url: string | null;
};

type CardFiltersResponse = {
  symbols: SymbolFilterOption[];
};

type CardDetail = {
  id: string;
  label: string;
  name: string;
};

type CardVersionDetail = CardVersionGalleryItemModel;

const route = useRoute();
const router = useRouter();
const card = ref<CardDetail | null>(null);
const versions = ref<CardVersionDetail[]>([]);
const symbolByKey = ref<Record<string, SymbolFilterOption>>({});

const goBack = (): void => {
  if (window.history.length > 1) {
    router.back();
    return;
  }
  void router.push('/cards');
};

const loadCard = async (): Promise<void> => {
  const cardId = String(route.params.id);
  const [cardResponse, versionsResponse, filtersResponse] = await Promise.all([
    api.get<CardDetail>(`/cards/${cardId}`),
    api.get<CardVersionDetail[]>(`/cards/${cardId}/generations`),
    api.get<CardFiltersResponse>('/cards/filters')
  ]);
  card.value = cardResponse.data;
  versions.value = versionsResponse.data;
  symbolByKey.value = Object.fromEntries(
    (filtersResponse.data.symbols ?? []).map((row) => [row.key, row])
  );
};

onMounted(loadCard);
watch(() => route.params.id, loadCard);
</script>
