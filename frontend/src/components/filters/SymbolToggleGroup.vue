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
        <p
          v-if="description"
          class="theme-section-muted text-xs"
        >
          {{ description }}
        </p>
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
          v-if="includedValue.length > 0"
          class="theme-pill theme-pill-accent px-2 py-0.5 text-xs font-medium"
        >
          +{{ includedValue.length }}
        </span>
        <span
          v-if="excludedValue.length > 0"
          class="theme-pill theme-pill-danger px-2 py-0.5 text-xs font-medium"
        >
          -{{ excludedValue.length }}
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
      <div class="flex flex-wrap gap-2">
        <button
          v-for="option in options"
          :key="option.id"
          type="button"
          class="theme-choice-chip h-10 w-10"
          :class="chipClass(option.id)"
          :title="chipTitle(option.label, option.id)"
          :aria-pressed="chipState(option.id) !== 'off'"
          :aria-label="chipTitle(option.label, option.id)"
          @click.stop="toggle(option.id)"
        >
          <SymbolToken
            :asset-url="option.asset_url"
            :label="option.label"
            :text-token="option.text_token"
            class="h-5 w-5 text-xs font-semibold"
          />
        </button>
      </div>

      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { ChevronDown, RotateCcw } from 'lucide-vue-next';
import SymbolToken from '@/components/SymbolToken.vue';
import type { SymbolFilterOption } from '@/modules/card-detail/types';
import type { SymbolFilterTriState } from '@/modules/card-search/cardFilterSectionsState';

const props = withDefaults(
  defineProps<{
    label: string;
    options: SymbolFilterOption[];
    includedValue: string[];
    excludedValue: string[];
    matchMode: 'any' | 'all';
    description?: string;
    defaultOpen?: boolean;
    showReset?: boolean;
  }>(),
  {
    description: '',
    defaultOpen: false,
    showReset: true,
  },
);

const emit = defineEmits<{
  (e: 'update:includedValue', value: string[]): void;
  (e: 'update:excludedValue', value: string[]): void;
  (e: 'update:matchMode', value: 'any' | 'all'): void;
  (e: 'reset'): void;
}>();

const includedIds = computed(() => new Set(props.includedValue));
const excludedIds = computed(() => new Set(props.excludedValue));
const isOpen = ref(props.defaultOpen);

const chipState = (id: string): SymbolFilterTriState => {
  if (includedIds.value.has(id)) {
    return 'include';
  }
  if (excludedIds.value.has(id)) {
    return 'exclude';
  }
  return 'off';
};

const chipTitle = (label: string, id: string): string => {
  const state = chipState(id);
  if (state === 'include') {
    return `${label} included. Click to exclude.`;
  }
  if (state === 'exclude') {
    return `${label} excluded. Click to clear.`;
  }
  return `${label} not filtered. Click to include.`;
};

const chipClass = (id: string): string => {
  const state = chipState(id);
  if (state === 'include') {
    return 'theme-choice-chip-include';
  }
  if (state === 'exclude') {
    return 'theme-choice-chip-exclude';
  }
  return '';
};

const toggle = (id: string): void => {
  const nextIncluded = new Set(props.includedValue);
  const nextExcluded = new Set(props.excludedValue);
  const state = chipState(id);

  if (state === 'include') {
    nextIncluded.delete(id);
    nextExcluded.add(id);
  } else if (state === 'exclude') {
    nextExcluded.delete(id);
  } else {
    nextIncluded.add(id);
    nextExcluded.delete(id);
  }

  emit('update:includedValue', Array.from(nextIncluded));
  emit('update:excludedValue', Array.from(nextExcluded));
};
</script>
