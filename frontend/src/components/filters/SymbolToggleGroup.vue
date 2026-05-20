<template>
  <section class="theme-muted-panel flex min-w-[12rem] flex-col gap-3">
    <button
      type="button"
      class="flex items-start justify-between gap-3 text-left"
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
      <div class="theme-section-muted flex items-center gap-2">
        <button
          v-if="showReset"
          type="button"
          class="rounded-full p-1 transition hover:bg-white hover:text-slate-900 dark:hover:bg-slate-800 dark:hover:text-slate-100"
          title="Reset group"
          aria-label="Reset group"
          @click.stop="emit('reset')"
        >
          <RotateCcw class="h-3.5 w-3.5" />
        </button>
        <span
          v-if="modelValue.length > 0"
          class="rounded-full bg-slate-900 px-2 py-0.5 text-xs font-medium text-white dark:bg-sky-500 dark:text-slate-950"
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
      class="space-y-3"
    >
      <div class="flex justify-end">
        <div class="flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-900/80">
          <button
            type="button"
            class="rounded-full px-3 py-1 text-xs font-medium transition"
            :class="matchMode === 'all' ? 'bg-slate-900 text-white dark:bg-sky-500 dark:text-slate-950' : 'text-slate-600 hover:bg-white dark:text-slate-300 dark:hover:bg-slate-800'"
            @click.stop="emit('update:matchMode', 'all')"
          >
            AND
          </button>
          <button
            type="button"
            class="rounded-full px-3 py-1 text-xs font-medium transition"
            :class="matchMode === 'any' ? 'bg-slate-900 text-white dark:bg-sky-500 dark:text-slate-950' : 'text-slate-600 hover:bg-white dark:text-slate-300 dark:hover:bg-slate-800'"
            @click.stop="emit('update:matchMode', 'any')"
          >
            OR
          </button>
        </div>
      </div>

      <div class="flex flex-wrap gap-2">
        <button
          v-for="option in options"
          :key="option.id"
          type="button"
          class="inline-flex h-10 w-10 items-center justify-center rounded-full border transition"
          :class="
            selectedIds.has(option.id)
              ? 'border-slate-900 bg-slate-900 text-white shadow-sm dark:border-sky-500 dark:bg-sky-500 dark:text-slate-950'
              : 'border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-slate-500 dark:hover:bg-slate-800'
          "
          :title="option.label"
          :aria-pressed="selectedIds.has(option.id)"
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

const props = withDefaults(
  defineProps<{
    label: string;
    options: SymbolFilterOption[];
    modelValue: string[];
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
  (e: 'update:modelValue', value: string[]): void;
  (e: 'update:matchMode', value: 'any' | 'all'): void;
  (e: 'reset'): void;
}>();

const selectedIds = computed(() => new Set(props.modelValue));
const isOpen = ref(props.defaultOpen);

const toggle = (id: string): void => {
  const next = new Set(props.modelValue);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  emit('update:modelValue', Array.from(next));
};
</script>
