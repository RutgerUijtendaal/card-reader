<template>
  <div>
    <button
      ref="triggerRef"
      type="button"
      class="btn-secondary inline-flex items-center gap-1.5 whitespace-nowrap px-3 py-2"
      @click="toggle"
    >
      <SlidersHorizontal class="h-4 w-4" />
      <span>View Options</span>
    </button>

    <Teleport to="body">
      <div
        v-if="isOpen"
        ref="panelRef"
        class="theme-popover z-30 w-80"
        :style="{ position: 'fixed', left: `${x}px`, top: `${y}px` }"
      >
        <div class="space-y-4">
          <label class="flex items-start justify-between gap-3">
            <div>
              <p class="theme-section-title text-sm font-semibold">
                Tooltip
              </p>
              <p class="theme-section-muted text-xs">
                Show card details on hover.
              </p>
            </div>
            <input
              :checked="tooltipEnabled"
              type="checkbox"
              class="theme-checkbox mt-1 h-4 w-4 rounded border-slate-300"
              @change="$emit('update:tooltipEnabled', ($event.target as HTMLInputElement).checked)"
            >
          </label>

          <label
            v-if="showCardGroupsControl"
            class="flex items-start justify-between gap-3"
          >
            <div>
              <p class="theme-section-title text-sm font-semibold">
                Card Groups
              </p>
              <p class="theme-section-muted text-xs">
                Show card groups as stacked gallery results.
              </p>
            </div>
            <input
              :checked="showCardGroups"
              type="checkbox"
              class="theme-checkbox mt-1 h-4 w-4 rounded border-slate-300"
              @change="$emit('update:showCardGroups', ($event.target as HTMLInputElement).checked)"
            >
          </label>

          <label class="block space-y-2">
            <div
              v-if="showPageSizeControl"
              class="space-y-2"
            >
              <div>
                <p class="theme-section-title text-sm font-semibold">
                  Cards Per Page
                </p>
                <p class="theme-section-muted text-xs">
                  Choose how many cards each gallery request loads.
                </p>
              </div>
              <select
                :value="pageSize ?? undefined"
                class="input-base w-full"
                @change="$emit('update:pageSize', Number(($event.target as HTMLSelectElement).value))"
              >
                <option
                  v-for="option in pageSizeOptions"
                  :key="option"
                  :value="option"
                >
                  {{ option }} cards
                </option>
              </select>
            </div>
          </label>

          <label class="block space-y-2">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="theme-section-title text-sm font-semibold">
                  Card Size
                </p>
                <p class="theme-section-muted text-xs">
                  Scale card display.
                </p>
              </div>
              <span class="theme-section-muted text-xs font-medium">
                {{ percentLabel }}
              </span>
            </div>
            <input
              :value="cardScale"
              type="range"
              min="0.8"
              max="1.2"
              step="0.05"
              class="theme-range w-full"
              @input="$emit('update:cardScale', Number(($event.target as HTMLInputElement).value))"
            >
          </label>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { SlidersHorizontal } from 'lucide-vue-next';
import { useFloatingPopover } from '@/composables/useFloatingPopover';
import { CARD_PAGE_SIZE_OPTIONS } from '@/modules/card-search/pageSize';

const props = withDefaults(
  defineProps<{
    tooltipEnabled: boolean;
    cardScale: number;
    showCardGroups: boolean;
    pageSize?: number | null;
    pageSizeOptions?: readonly number[];
    showCardGroupsControl?: boolean;
    showPageSizeControl?: boolean;
  }>(),
  {
    pageSize: null,
    pageSizeOptions: () => [...CARD_PAGE_SIZE_OPTIONS],
    showCardGroupsControl: true,
    showPageSizeControl: false,
  },
);

defineEmits<{
  (e: 'update:tooltipEnabled', value: boolean): void;
  (e: 'update:cardScale', value: number): void;
  (e: 'update:showCardGroups', value: boolean): void;
  (e: 'update:pageSize', value: number): void;
}>();

const { isOpen, triggerRef, panelRef, x, y, toggle } = useFloatingPopover({
  placement: 'bottom-start',
});
const percentLabel = computed(() => `${Math.round(props.cardScale * 100)}%`);
</script>
