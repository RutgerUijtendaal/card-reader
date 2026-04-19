<template>
  <section class="space-y-6">
    <div class="page-card sticky top-0 z-20 space-y-4">
      <h2 class="flex items-center gap-2 text-xl font-semibold text-slate-900">
        <Images class="h-5 w-5 text-slate-500" />
        <span>Card Gallery</span>
      </h2>

      <div class="grid grid-cols-1 gap-3 2xl:grid-cols-[minmax(0,1fr)_auto] 2xl:items-center">
        <div class="order-2 flex flex-wrap gap-2 2xl:order-1">
          <FilterMultiSelectPopover v-model="selectedKeywordIds" label="Keywords" :options="filters.keywords" empty-text="No keywords available." />
          <FilterMultiSelectPopover v-model="selectedTagIds" label="Tags" :options="filters.tags" empty-text="No tags available." />
          <FilterMultiSelectPopover v-model="selectedTypeIds" label="Types" :options="filters.types" empty-text="No types available." />
          <FilterMultiSelectPopover v-model="selectedManaTypeSymbolIds" label="Mana Type" :options="manaTypeOptions" empty-text="No mana symbols available." />
          <FilterMultiSelectPopover v-model="selectedAffinitySymbolIds" label="Affinity" :options="affinityTypeOptions" empty-text="No affinity symbols available." />
          <FilterTextPopover v-model="manaCost" label="Mana Cost" placeholder="e.g. 3RR" />
          <FilterTextPopover v-model="templateId" label="Template" placeholder="mtg-like-v1" />
          <FilterTextPopover v-model="attackMin" label="Attack ≥" input-type="number" />
          <FilterTextPopover v-model="attackMax" label="Attack ≤" input-type="number" />
          <FilterTextPopover v-model="healthMin" label="Health ≥" input-type="number" />
          <FilterTextPopover v-model="healthMax" label="Health ≤" input-type="number" />
        </div>

        <div class="order-1 flex min-w-0 flex-nowrap items-center gap-2 2xl:order-2 2xl:min-w-[26rem] 2xl:justify-end">
          <input v-model="query" class="input-base min-w-[14rem] flex-1 2xl:w-80 2xl:flex-none" placeholder="Search cards..." />
          <span class="whitespace-nowrap text-xs text-slate-500">{{ cards.length }} results</span>
          <button class="btn-secondary inline-flex items-center gap-2 whitespace-nowrap" type="button" @click="exportCsv">
            <Download class="h-4 w-4" />
            <span>Export CSV</span>
          </button>
          <button class="btn-secondary inline-flex items-center gap-2 whitespace-nowrap" type="button" @click="resetFilters">
            <RotateCcw class="h-4 w-4" />
            <span>Reset</span>
          </button>
        </div>
      </div>
    </div>

    <div class="flex flex-wrap items-start gap-5">
      <CardGalleryItem
        v-for="card in cards"
        :key="card.id"
        :card="card"
        :symbol-by-key="symbolByKey"
      />
    </div>

    <div v-if="cards.length === 0" class="page-card text-sm text-slate-500">
      No cards found for the current filters.
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue';
import { Download, Images, RotateCcw } from 'lucide-vue-next';
import { api } from '@/api/client';
import { useCsvExport } from '@/composables/useCsvExport';
import FilterMultiSelectPopover from '@/components/filters/FilterMultiSelectPopover.vue';
import FilterTextPopover from '@/components/filters/FilterTextPopover.vue';
import CardGalleryItem, { type CardGalleryItemModel } from '@/components/cards/CardGalleryItem.vue';

type MetadataOption = {
  id: string;
  key: string;
  label: string;
};

type SymbolFilterOption = MetadataOption & {
  symbol_type: string;
  text_token: string;
  asset_url: string | null;
};

type CardFiltersResponse = {
  keywords: MetadataOption[];
  tags: MetadataOption[];
  symbols: SymbolFilterOption[];
  types: MetadataOption[];
};

const query = ref('');
const manaCost = ref('');
const templateId = ref('');
const attackMin = ref('');
const attackMax = ref('');
const healthMin = ref('');
const healthMax = ref('');

const selectedKeywordIds = ref<string[]>([]);
const selectedTagIds = ref<string[]>([]);
const selectedManaTypeSymbolIds = ref<string[]>([]);
const selectedAffinitySymbolIds = ref<string[]>([]);
const selectedTypeIds = ref<string[]>([]);

const filters = ref<CardFiltersResponse>({
  keywords: [],
  tags: [],
  symbols: [],
  types: []
});
const cards = ref<CardGalleryItemModel[]>([]);
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;
const { exportCardsCsv } = useCsvExport();
const symbolByKey = computed<Record<string, SymbolFilterOption>>(() =>
  Object.fromEntries((filters.value.symbols ?? []).map((row) => [row.key, row]))
);

const manaTypeOptions = computed<MetadataOption[]>(() =>
  (filters.value.symbols ?? []).filter((row) => row.symbol_type === 'mana')
);

const affinityTypeOptions = computed<MetadataOption[]>(() =>
  (filters.value.symbols ?? []).filter((row) => row.symbol_type === 'affinity')
);

const loadFilters = async (): Promise<void> => {
  const response = await api.get<CardFiltersResponse>('/cards/filters');
  filters.value = response.data;
};

const buildSearchParams = (): URLSearchParams => {
  const params = new URLSearchParams();
  if (query.value.trim()) params.set('q', query.value.trim());
  if (manaCost.value.trim()) params.set('mana_cost', manaCost.value.trim());
  if (templateId.value.trim()) params.set('template_id', templateId.value.trim());
  if (attackMin.value.trim()) params.set('attack_min', attackMin.value.trim());
  if (attackMax.value.trim()) params.set('attack_max', attackMax.value.trim());
  if (healthMin.value.trim()) params.set('health_min', healthMin.value.trim());
  if (healthMax.value.trim()) params.set('health_max', healthMax.value.trim());

  selectedKeywordIds.value.forEach((id) => params.append('keyword_ids', id));
  selectedTagIds.value.forEach((id) => params.append('tag_ids', id));
  const selectedSymbolIds = new Set<string>([
    ...selectedManaTypeSymbolIds.value,
    ...selectedAffinitySymbolIds.value
  ]);
  selectedSymbolIds.forEach((id) => params.append('symbol_ids', id));
  selectedTypeIds.value.forEach((id) => params.append('type_ids', id));

  return params;
};

const searchCards = async (): Promise<void> => {
  const params = buildSearchParams().toString();
  const path = params ? `/cards?${params}` : '/cards';
  const response = await api.get<CardGalleryItemModel[]>(path);
  cards.value = response.data;
};

const exportCsv = async (): Promise<void> => {
  await exportCardsCsv(buildSearchParams());
};

const debouncedSearch = (): void => {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer);
  }
  searchDebounceTimer = setTimeout(() => {
    void searchCards();
  }, 250);
};

const observedFilterState = computed(() => ({
  query: query.value.trim(),
  manaCost: manaCost.value.trim(),
  templateId: templateId.value.trim(),
  attackMin: attackMin.value.trim(),
  attackMax: attackMax.value.trim(),
  healthMin: healthMin.value.trim(),
  healthMax: healthMax.value.trim(),
  keywordIds: [...selectedKeywordIds.value].sort(),
  tagIds: [...selectedTagIds.value].sort(),
  manaTypeSymbolIds: [...selectedManaTypeSymbolIds.value].sort(),
  affinitySymbolIds: [...selectedAffinitySymbolIds.value].sort(),
  typeIds: [...selectedTypeIds.value].sort()
}));

watch(
  observedFilterState,
  () => {
    debouncedSearch();
  },
  { deep: true }
);

const resetFilters = (): void => {
  query.value = '';
  manaCost.value = '';
  templateId.value = '';
  attackMin.value = '';
  attackMax.value = '';
  healthMin.value = '';
  healthMax.value = '';
  selectedKeywordIds.value = [];
  selectedTagIds.value = [];
  selectedManaTypeSymbolIds.value = [];
  selectedAffinitySymbolIds.value = [];
  selectedTypeIds.value = [];
};

onMounted(async () => {
  await loadFilters();
  await searchCards();
});

onBeforeUnmount(() => {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer);
  }
});
</script>
