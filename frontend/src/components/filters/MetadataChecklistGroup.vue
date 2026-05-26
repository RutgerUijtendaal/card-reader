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
        <label
          v-for="option in filteredOptions"
          :key="option.id"
          class="theme-checkbox-row"
        >
          <input
            :checked="selectedIds.has(option.id)"
            type="checkbox"
            class="theme-checkbox mt-0.5 h-4 w-4 rounded border-slate-300"
            @change="toggle(option.id)"
          >
          <span>{{ option.label }}</span>
        </label>
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
import { ChevronDown, RotateCcw } from 'lucide-vue-next';

type Option = {
  id: string;
  label: string;
};

const props = withDefaults(
  defineProps<{
    label: string;
    options: Option[];
    modelValue: string[];
    matchMode: 'any' | 'all';
    defaultOpen?: boolean;
    showReset?: boolean;
  }>(),
  {
    defaultOpen: false,
    showReset: true,
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void;
  (e: 'update:matchMode', value: 'any' | 'all'): void;
  (e: 'reset'): void;
}>();

const isOpen = ref(props.defaultOpen);
const searchTerm = ref('');
const selectedIds = computed(() => new Set(props.modelValue));

watch(isOpen, (open) => {
  if (!open) {
    searchTerm.value = '';
  }
});

const filteredOptions = computed(() => {
  const term = searchTerm.value.trim().toLowerCase();
  if (!term) {
    return props.options;
  }
  return props.options.filter((option) => option.label.toLowerCase().includes(term));
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
</script>
