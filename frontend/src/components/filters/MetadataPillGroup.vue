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
          v-if="includedValue.length > 0"
          class="theme-pill theme-pill-accent px-2 py-0.5 text-xs font-medium"
        >
          +{{ includedValue.length }}
        </span>
        <span
          v-if="excludedValue.length > 0"
          class="theme-pill theme-pill-filter-exclude px-2 py-0.5 text-xs font-medium"
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
      <div
        v-if="groups.length > 0"
        class="space-y-3"
      >
        <div
          v-for="group in groups"
          :key="group.key"
          class="space-y-2"
        >
          <p class="theme-kicker text-[11px] font-semibold uppercase tracking-[0.16em]">
            {{ group.label }}
          </p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="option in group.options"
              :key="option.id"
              type="button"
              class="theme-choice-chip inline-flex min-h-10 items-center gap-1 px-3 py-2"
              :class="chipClass(option.id, group.selectedClass)"
              :title="chipTitle(option.label, option.id)"
              :aria-pressed="chipState(option.id) !== 'off'"
              :aria-label="chipTitle(option.label, option.id)"
              @click.stop="toggle(option.id)"
            >
              <span
                v-if="chipState(option.id) !== 'off'"
                aria-hidden="true"
              >
                {{ chipState(option.id) === 'include' ? '+' : '−' }}
              </span>
              {{ option.label }}
            </button>
          </div>
        </div>
      </div>

      <div
        v-else-if="visibleOptions.length > 0"
        class="flex flex-wrap gap-2"
      >
        <button
          v-for="option in visibleOptions"
          :key="option.id"
          type="button"
          class="theme-choice-chip inline-flex min-h-10 items-center gap-1 px-3 py-2"
          :class="chipClass(option.id)"
          :title="chipTitle(option.label, option.id)"
          :aria-pressed="chipState(option.id) !== 'off'"
          :aria-label="chipTitle(option.label, option.id)"
          @click.stop="toggle(option.id)"
        >
          <span
            v-if="chipState(option.id) !== 'off'"
            aria-hidden="true"
          >
            {{ chipState(option.id) === 'include' ? '+' : '−' }}
          </span>
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
import {
  getTriStateSelection,
  getTriStateSelectionClass,
  getTriStateSelectionLabel,
  toggleTriStateSelection,
  type TriStateSelection,
} from '@/composables/card-filters/triStateSelection';
import type { MetadataOption } from '@/modules/card-detail/types';

export type MetadataPillOptionGroup = {
  key: string;
  label: string;
  options: MetadataOption[];
  selectedClass: string;
};

const props = withDefaults(
  defineProps<{
    label: string;
    options: MetadataOption[];
    includedValue: string[];
    excludedValue: string[];
    matchMode: 'any' | 'all';
    defaultOpen?: boolean;
    showReset?: boolean;
    initialVisibleCount?: number;
    groups?: MetadataPillOptionGroup[];
  }>(),
  {
    defaultOpen: false,
    showReset: true,
    initialVisibleCount: 10,
    groups: () => [],
  },
);

const emit = defineEmits<{
  (e: 'update:includedValue', value: string[]): void;
  (e: 'update:excludedValue', value: string[]): void;
  (e: 'update:matchMode', value: 'any' | 'all'): void;
  (e: 'reset'): void;
}>();

const isOpen = ref(props.defaultOpen);
const isExpanded = ref(false);
const activeIds = computed(() => new Set([...props.includedValue, ...props.excludedValue]));

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
    (option, index) => index >= props.initialVisibleCount && activeIds.value.has(option.id),
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

const chipState = (id: string): TriStateSelection =>
  getTriStateSelection(id, props.includedValue, props.excludedValue);

const chipTitle = (label: string, id: string): string =>
  getTriStateSelectionLabel(label, chipState(id));

const chipClass = (id: string, includedClass = 'theme-choice-chip-include'): string => {
  const state = chipState(id);
  return state === 'include' ? includedClass : getTriStateSelectionClass(state);
};

const toggle = (id: string): void => {
  const next = toggleTriStateSelection(id, props.includedValue, props.excludedValue);
  emit('update:includedValue', next.included);
  emit('update:excludedValue', next.excluded);
};
</script>
