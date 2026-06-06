<template>
  <section class="theme-muted-panel flex min-w-[12rem] flex-col gap-3">
    <button
      type="button"
      class="flex min-h-9 items-center justify-between gap-2 text-left"
      @click="isOpen = !isOpen"
    >
      <div class="min-w-0">
        <h3 class="theme-section-title text-sm font-semibold">
          {{ label }}
        </h3>
      </div>
      <div class="theme-section-muted flex min-h-9 items-center gap-2">
        <div
          v-if="isOpen"
          class="theme-toggle-shell theme-toggle-shell-compact"
        >
          <button
            type="button"
            class="theme-toggle-option theme-toggle-option-compact"
            :class="matchMode === 'all' ? 'theme-toggle-option-active' : ''"
            @click.stop="emit('update:matchMode', 'all')"
          >
            AND
          </button>
          <button
            type="button"
            class="theme-toggle-option theme-toggle-option-compact"
            :class="matchMode === 'any' ? 'theme-toggle-option-active' : ''"
            @click.stop="emit('update:matchMode', 'any')"
          >
            OR
          </button>
        </div>
        <button
          v-if="showReset"
          type="button"
          class="theme-icon-button"
          title="Reset group"
          aria-label="Reset group"
          @click.stop="emit('reset')"
        >
          <RotateCcw class="h-3.5 w-3.5" />
        </button>
        <span
          v-if="modelValue.length > 0"
          class="theme-pill theme-pill-accent px-2 py-0.5 text-xs font-medium"
        >
          {{ modelValue.length }}
        </span>
        <ChevronDown
          class="h-4 w-4 transition"
          :class="isOpen ? 'rotate-180' : ''"
        />
      </div>
    </button>

    <div
      v-if="isOpen"
      class="theme-divider space-y-3 border-t pt-3"
    >
      <input
        v-model="searchTerm"
        class="input-base"
        :placeholder="`Search ${label.toLowerCase()}...`"
      >

      <div
        v-if="filteredOptions.length > 0"
        class="app-scrollbar h-64 space-y-2 overflow-auto pr-1"
      >
        <div
          v-for="option in filteredOptions"
          :key="option.id"
          class="theme-checkbox-row group justify-between gap-2"
          :data-option-key="option.key"
        >
          <label class="flex min-w-0 flex-1 cursor-pointer items-start gap-3">
            <input
              :checked="selectedIds.has(option.id)"
              type="checkbox"
              class="theme-checkbox mt-0.5 h-4 w-4 rounded border-slate-300"
              @change="toggle(option.id)"
            >
            <span class="min-w-0 flex-1">
              {{ option.label }}
            </span>
          </label>
          <button
            v-if="favoriteGroup"
            type="button"
            class="theme-filter-favorite-button shrink-0"
            :class="isFavorited(option.key) ? 'theme-filter-favorite-button-active' : ''"
            :aria-label="`${isFavorited(option.key) ? 'Remove favorite' : 'Add favorite'} ${option.label}`"
            :title="`${isFavorited(option.key) ? 'Remove favorite' : 'Add favorite'} ${option.label}`"
            @click.stop.prevent="handleFavoriteClick($event, option.key)"
          >
            <Star
              class="h-4 w-4"
              :fill="isFavorited(option.key) ? 'currentColor' : 'none'"
            />
          </button>
        </div>
      </div>

      <p
        v-else
        class="theme-empty-state flex h-64 items-center"
      >
        {{ emptyState }}
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ChevronDown, RotateCcw, Star } from 'lucide-vue-next';
import type { MetadataOption } from '@/modules/card-detail/types';
import type { MetadataFavoriteGroup } from '@/composables/card-filters/useMetadataFilterFavorites';
import { blurAfterFinePointerActivation } from '@/utils/pointerFocus';

const props = withDefaults(
  defineProps<{
    label: string;
    options: MetadataOption[];
    modelValue: string[];
    matchMode: 'any' | 'all';
    defaultOpen?: boolean;
    showReset?: boolean;
    favoriteGroup?: MetadataFavoriteGroup;
    favoriteKeys?: string[];
  }>(),
  {
    defaultOpen: false,
    showReset: true,
    favoriteGroup: undefined,
    favoriteKeys: () => [],
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void;
  (e: 'update:matchMode', value: 'any' | 'all'): void;
  (e: 'toggle-favorite', value: string): void;
  (e: 'reset'): void;
}>();

const isOpen = ref(props.defaultOpen);
const searchTerm = ref('');
const selectedIds = computed(() => new Set(props.modelValue));
const favoriteKeysSet = computed(() => new Set(props.favoriteKeys));

watch(isOpen, (open) => {
  if (!open) {
    searchTerm.value = '';
  }
});

const filteredOptions = computed(() => {
  const term = searchTerm.value.trim().toLowerCase();
  const matchingOptions = !term
    ? props.options
    : props.options.filter((option) => option.label.toLowerCase().includes(term));

  const favoriteOptions = matchingOptions.filter((option) => favoriteKeysSet.value.has(option.key));
  const normalOptions = matchingOptions.filter((option) => !favoriteKeysSet.value.has(option.key));
  return [...favoriteOptions, ...normalOptions];
});

const emptyState = computed(() =>
  props.options.length === 0 ? `No ${props.label.toLowerCase()} available.` : 'No matches.',
);

const toggle = (id: string): void => {
  const next = new Set(props.modelValue);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  emit('update:modelValue', Array.from(next));
};

const isFavorited = (key: string): boolean => favoriteKeysSet.value.has(key);

const handleFavoriteClick = (event: MouseEvent, key: string): void => {
  emit('toggle-favorite', key);
  blurAfterFinePointerActivation(event);
};
</script>
