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
      </div>
      <div class="theme-section-muted flex items-center gap-2">
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
          class="theme-pill theme-pill-neutral px-2 py-0.5 text-xs font-medium"
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
        <div class="theme-toggle-shell">
          <button
            type="button"
            class="theme-toggle-option"
            :class="matchMode === 'all' ? 'theme-toggle-option-active' : ''"
            @click.stop="emit('update:matchMode', 'all')"
          >
            AND
          </button>
          <button
            type="button"
            class="theme-toggle-option"
            :class="matchMode === 'any' ? 'theme-toggle-option-active' : ''"
            @click.stop="emit('update:matchMode', 'any')"
          >
            OR
          </button>
        </div>
      </div>

      <div
        v-if="visibleOptions.length > 0"
        class="flex flex-wrap gap-2"
      >
        <button
          v-for="option in visibleOptions"
          :key="option.id"
          type="button"
          class="theme-choice-chip min-h-10 px-3 py-2"
          :class="
            selectedIds.has(option.id)
              ? 'theme-choice-chip-active shadow-sm'
              : ''
          "
          :aria-pressed="selectedIds.has(option.id)"
          @click.stop="toggle(option.id)"
        >
          {{ option.label }}
        </button>

        <button
          v-if="hiddenOptionCount > 0"
          type="button"
          class="theme-choice-chip theme-choice-chip-dashed min-h-10 px-3 py-2"
          @click.stop="isExpanded = true"
        >
          More
        </button>

        <button
          v-else-if="canCollapse"
          type="button"
          class="theme-choice-chip theme-choice-chip-dashed min-h-10 px-3 py-2"
          @click.stop="isExpanded = false"
        >
          Less
        </button>
      </div>

      <p
        v-else
        class="theme-empty-state"
      >
        No {{ label.toLowerCase() }} available.
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ChevronDown, RotateCcw } from 'lucide-vue-next';
import type { MetadataOption } from '@/modules/card-detail/types';

const props = withDefaults(
  defineProps<{
    label: string;
    options: MetadataOption[];
    modelValue: string[];
    matchMode: 'any' | 'all';
    defaultOpen?: boolean;
    showReset?: boolean;
    initialVisibleCount?: number;
  }>(),
  {
    defaultOpen: false,
    showReset: true,
    initialVisibleCount: 10,
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void;
  (e: 'update:matchMode', value: 'any' | 'all'): void;
  (e: 'reset'): void;
}>();

const isOpen = ref(props.defaultOpen);
const isExpanded = ref(false);
const selectedIds = computed(() => new Set(props.modelValue));

watch(isOpen, (open) => {
  if (!open) {
    isExpanded.value = false;
  }
});

const visibleOptions = computed(() => {
  if (props.options.length <= props.initialVisibleCount || isExpanded.value) {
    return props.options;
  }

  const selectedOutsideTop = props.options.filter(
    (option, index) => index >= props.initialVisibleCount && selectedIds.value.has(option.id),
  );

  return [...props.options.slice(0, props.initialVisibleCount), ...selectedOutsideTop];
});

const hiddenOptionCount = computed(() => {
  if (isExpanded.value || props.options.length <= props.initialVisibleCount) {
    return 0;
  }
  return props.options.length - visibleOptions.value.length;
});

const canCollapse = computed(
  () => isExpanded.value && props.options.length > props.initialVisibleCount,
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
