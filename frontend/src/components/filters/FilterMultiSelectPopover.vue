<template>
  <div class="relative inline-block">
    <button
      ref="triggerRef"
      type="button"
      class="filter-chip"
      :class="
        isActive
          ? 'border-sky-300 bg-sky-50 text-sky-700'
          : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100'
      "
      @click="toggle"
    >
      {{ label }} <span v-if="selectedCount">({{ selectedCount }})</span>
    </button>

    <Teleport to="body">
      <div
        v-if="isOpen"
        ref="panelRef"
        class="z-50 w-72 rounded-lg border border-slate-200 bg-white p-3 shadow-xl"
        :style="{ position: 'fixed', left: `${x}px`, top: `${y}px` }"
      >
        <div class="space-y-2">
          <input
            v-model="searchTerm"
            class="input-base"
            :placeholder="`Search ${label.toLowerCase()}...`"
          >

          <div class="max-h-64 space-y-1 overflow-auto pr-1">
            <label
              v-for="option in filteredOptions"
              :key="option.id"
              class="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm text-slate-700 hover:bg-slate-100"
            >
              <input
                :checked="selectedSet.has(option.id)"
                type="checkbox"
                class="h-4 w-4 rounded border-slate-300 text-sky-600"
                @change="toggleOption(option.id)"
              >
              <span>{{ option.label }}</span>
            </label>
          </div>

          <p
            v-if="options.length === 0"
            class="text-xs text-slate-400"
          >
            {{ emptyText }}
          </p>
          <p
            v-else-if="filteredOptions.length === 0"
            class="text-xs text-slate-400"
          >
            No matches.
          </p>

          <div
            v-if="matchMode"
            class="border-t border-slate-200 pt-2"
          >
            <div class="flex justify-end">
              <div class="flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 p-1">
                <button
                  class="rounded-full px-3 py-1 text-xs font-medium transition"
                  :class="matchMode === 'any' ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-white'"
                  type="button"
                  @click="setMatchMode('any')"
                >
                  OR
                </button>
                <button
                  class="rounded-full px-3 py-1 text-xs font-medium transition"
                  :class="matchMode === 'all' ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-white'"
                  type="button"
                  @click="setMatchMode('all')"
                >
                  AND
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useFloatingPopover } from '@/composables/useFloatingPopover';

type Option = {
  id: string;
  label: string;
};

const props = withDefaults(
  defineProps<{
    label: string;
    options: Option[];
    modelValue: string[];
    matchMode?: 'any' | 'all';
    emptyText?: string;
  }>(),
  {
    emptyText: 'No options available.',
    matchMode: undefined,
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void;
  (e: 'update:matchMode', value: 'any' | 'all'): void;
}>();

const { isOpen, triggerRef, panelRef, x, y, toggle } = useFloatingPopover();
const searchTerm = ref('');

watch(isOpen, (open) => {
  if (!open) searchTerm.value = '';
});

const selectedSet = computed(() => new Set(props.modelValue));
const selectedCount = computed(() => props.modelValue.length);
const isActive = computed(() => selectedCount.value > 0);

const filteredOptions = computed(() => {
  const term = searchTerm.value.trim().toLowerCase();
  if (!term) return props.options;
  return props.options.filter((option) => option.label.toLowerCase().includes(term));
});

const toggleOption = (id: string): void => {
  const next = new Set(props.modelValue);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  emit('update:modelValue', Array.from(next));
};

const setMatchMode = (value: 'any' | 'all'): void => {
  emit('update:matchMode', value);
};
</script>

<style scoped>
.filter-chip {
  @apply rounded-md border px-3 py-1.5 text-xs font-semibold transition;
}
</style>
