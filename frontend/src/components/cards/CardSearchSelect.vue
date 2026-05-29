<template>
  <div class="relative">
    <label class="field-label">
      {{ label }}
      <input
        ref="triggerRef"
        v-model="query"
        class="input-base"
        :placeholder="placeholder"
        :disabled="disabled"
        autocomplete="off"
        @focus="openResults"
        @keydown.enter.prevent
      >
    </label>

    <Teleport to="body">
      <div
        v-if="isOpen"
        ref="panelRef"
        class="theme-popover z-40 p-2"
        :style="{ position: 'fixed', left: `${x}px`, top: `${y}px`, width: `${panelWidth}px` }"
      >
        <div class="app-scrollbar max-h-80 space-y-2 overflow-y-auto pr-1">
          <p
            v-if="query.trim().length === 0"
            class="theme-section-muted px-2 py-3 text-sm"
          >
            Start typing to search cards.
          </p>
          <p
            v-else-if="searching"
            class="theme-section-muted px-2 py-3 text-sm"
          >
            Searching...
          </p>
          <p
            v-else-if="results.length === 0"
            class="theme-section-muted px-2 py-3 text-sm"
          >
            No cards found.
          </p>
          <SmallCardSearchResultRow
            v-for="card in results"
            :key="card.id"
            :card="card"
            :disabled="disabledCardIdsSet.has(card.id)"
            :action-label="disabledCardIdsSet.has(card.id) ? disabledActionLabel : 'Select'"
            :aria-label="`${disabledCardIdsSet.has(card.id) ? disabledActionLabel : 'Select'} ${card.name}`"
            @activate="selectCard"
          />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from '@floating-ui/vue';
import { onClickOutside, useDebounceFn } from '@vueuse/core';
import { computed, ref, watch } from 'vue';
import { api } from '@/api/client';
import SmallCardSearchResultRow from '@/components/cards/SmallCardSearchResultRow.vue';
import { managementCardSearchLifecycleParams } from '@/modules/card-filters/cardLifecycle';
import type { CardListItem, PaginatedCardsResponse } from '@/modules/card-detail/types';

const props = withDefaults(defineProps<{
  label: string;
  placeholder?: string;
  disabled?: boolean;
  disabledCardIds?: string[];
  disabledActionLabel?: string;
  pageSize?: number;
  selectionMode?: 'single' | 'multi';
}>(), {
  placeholder: 'Search cards...',
  disabled: false,
  disabledCardIds: () => [],
  disabledActionLabel: 'Unavailable',
  pageSize: 12,
  selectionMode: 'single',
});

const emit = defineEmits<{
  (e: 'select', card: CardListItem): void;
}>();

const query = ref('');
const results = ref<CardListItem[]>([]);
const searching = ref(false);
const isOpen = ref(false);
const suppressNextQuerySearch = ref(false);
const triggerRef = ref<HTMLElement | null>(null);
const panelRef = ref<HTMLElement | null>(null);
const panelWidth = ref(320);
const disabledCardIdsSet = computed(() => new Set(props.disabledCardIds));
const floating = useFloating(triggerRef, panelRef, {
  open: isOpen,
  placement: 'bottom-start',
  strategy: 'fixed',
  middleware: [offset(8), flip(), shift({ padding: 8 })],
  whileElementsMounted: autoUpdate,
});
const x = computed(() => floating.x.value ?? 0);
const y = computed(() => floating.y.value ?? 0);

const runSearch = async (): Promise<void> => {
  const searchTerm = query.value.trim();
  if (props.disabled || searchTerm.length === 0) {
    results.value = [];
    searching.value = false;
    return;
  }

  searching.value = true;
  try {
    const response = await api.get<PaginatedCardsResponse<CardListItem>>('/cards', {
      params: {
        q: searchTerm,
        ...managementCardSearchLifecycleParams(),
        page: 1,
        page_size: props.pageSize,
      },
    });
    results.value = response.data.results.filter((item): item is CardListItem => item.result_type === 'card');
  } finally {
    searching.value = false;
  }
};

const debouncedSearch = useDebounceFn(() => {
  void runSearch();
}, 250);

const openResults = (): void => {
  if (props.disabled) {
    return;
  }
  panelWidth.value = triggerRef.value?.getBoundingClientRect().width ?? 320;
  isOpen.value = true;
};

const closeResults = (): void => {
  isOpen.value = false;
};

const selectCard = (card: CardListItem): void => {
  if (disabledCardIdsSet.value.has(card.id)) {
    return;
  }
  emit('select', card);
  if (props.selectionMode === 'single') {
    suppressNextQuerySearch.value = true;
    query.value = card.name;
    results.value = [];
    closeResults();
  }
};

onClickOutside(panelRef, (event) => {
  const target = event.target as Node | null;
  if (target && triggerRef.value?.contains(target)) {
    return;
  }
  closeResults();
});

watch(query, () => {
  if (suppressNextQuerySearch.value) {
    suppressNextQuerySearch.value = false;
    return;
  }
  if (!isOpen.value && query.value.trim().length > 0) {
    openResults();
  }
  debouncedSearch();
});

watch(
  () => props.disabled,
  (isDisabled) => {
    if (isDisabled) {
      query.value = '';
      results.value = [];
      closeResults();
    }
  },
);
</script>
