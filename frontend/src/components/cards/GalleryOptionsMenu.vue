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
        class="theme-popover z-30 w-[22rem]"
        :style="{ position: 'fixed', left: `${x}px`, top: `${y}px` }"
      >
        <div class="space-y-4">
          <div class="space-y-1">
            <p class="theme-section-title text-sm font-semibold">
              View Options
            </p>
            <p class="theme-section-muted text-xs">
              Adjust hover behavior and gallery display for this view.
            </p>
          </div>

          <PopoverOptionList
            title="Hover Preview"
            description="Choose how card hover should behave."
            appearance="list"
            :options="hoverModeMenuOptions"
            :selected-value="hoverMode"
            :selection-active="hoverModeOverrideActive"
            :default-option="allowHoverModeDefaultOption ? { label: 'Use Global Default', description: defaultHoverModeLabel } : null"
            @select="handleHoverModeSelect"
            @reset="handleHoverModeReset"
          />

          <section class="space-y-2">
            <div>
              <p class="theme-section-title text-sm font-semibold">
                Display
              </p>
              <p class="theme-section-muted text-xs">
                Fine-tune how cards are laid out in the current view.
              </p>
            </div>

            <div class="theme-muted-panel space-y-0 p-0">
              <label
                v-if="showCardGroupsControl"
                class="flex items-start justify-between gap-4 px-3 py-3"
              >
                <div class="min-w-0">
                  <p class="theme-section-title text-sm font-semibold">
                    Card Groups
                  </p>
                  <p class="theme-section-muted mt-1 text-xs">
                    Show grouped cards as stacked gallery results.
                  </p>
                </div>
                <input
                  :checked="showCardGroups"
                  type="checkbox"
                  class="theme-checkbox mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300"
                  @change="emit('update:showCardGroups', ($event.target as HTMLInputElement).checked)"
                >
              </label>

              <div
                v-if="showPageSizeControl"
                class="theme-divider border-t px-3 py-3"
              >
                <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <div class="min-w-0">
                    <p class="theme-section-title text-sm font-semibold">
                      Cards Per Page
                    </p>
                    <p class="theme-section-muted mt-1 text-xs">
                      Choose how many cards each gallery request loads.
                    </p>
                  </div>
                  <AppSelect
                    :model-value="pageSize ?? null"
                    :options="pageSizeSelectOptions"
                    wrapper-class="w-full sm:ml-auto sm:w-[7rem] sm:shrink-0"
                    @update:model-value="handlePageSizeChange"
                  />
                </div>
              </div>

              <div
                class="theme-divider border-t px-3 py-3"
                :class="showCardGroupsControl || showPageSizeControl ? '' : 'border-t-0'"
              >
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <p class="theme-section-title text-sm font-semibold">
                      Card Size
                    </p>
                    <p class="theme-section-muted mt-1 text-xs">
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
                  class="theme-range mt-3 w-full"
                  @input="emit('update:cardScale', Number(($event.target as HTMLInputElement).value))"
                >
              </div>
            </div>
          </section>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { SlidersHorizontal } from 'lucide-vue-next';
import AppSelect from '@/components/app/AppSelect.vue';
import PopoverOptionList, { type PopoverOptionItem } from '@/components/cards/PopoverOptionList.vue';
import { useFloatingPopover } from '@/composables/useFloatingPopover';
import { HOVER_MODE_OPTIONS, type HoverMode } from '@/composables/card-gallery/hoverMode';
import { CARD_PAGE_SIZE_OPTIONS } from '@/composables/card-gallery/pageSize';

const props = withDefaults(
  defineProps<{
    hoverMode: HoverMode;
    defaultHoverMode?: HoverMode | null;
    hoverModeOverrideActive?: boolean;
    allowHoverModeDefaultOption?: boolean;
    cardScale: number;
    showCardGroups: boolean;
    pageSize?: number | null;
    pageSizeOptions?: readonly number[];
    showCardGroupsControl?: boolean;
    showPageSizeControl?: boolean;
  }>(),
  {
    defaultHoverMode: null,
    hoverModeOverrideActive: true,
    allowHoverModeDefaultOption: false,
    pageSize: null,
    pageSizeOptions: () => [...CARD_PAGE_SIZE_OPTIONS],
    showCardGroupsControl: true,
    showPageSizeControl: false,
  },
);

const emit = defineEmits<{
  (e: 'update:hoverMode', value: HoverMode): void;
  (e: 'reset:hoverMode'): void;
  (e: 'update:cardScale', value: number): void;
  (e: 'update:showCardGroups', value: boolean): void;
  (e: 'update:pageSize', value: number): void;
}>();

const { isOpen, triggerRef, panelRef, x, y, toggle, close } = useFloatingPopover({
  placement: 'bottom-start',
});
const hoverModeOptions = HOVER_MODE_OPTIONS;
const hoverModeMenuOptions = computed<PopoverOptionItem[]>(() =>
  hoverModeOptions.map((option) => ({
    value: option.value,
    label: option.label,
  })),
);
const pageSizeSelectOptions = computed(() =>
  props.pageSizeOptions.map((option) => ({
    value: option,
    label: `${option} cards`,
  })),
);
const defaultHoverModeLabel = computed(() =>
  props.defaultHoverMode === null
    ? 'No default selected'
    : (hoverModeOptions.find((option) => option.value === props.defaultHoverMode)?.label ?? props.defaultHoverMode),
);
const percentLabel = computed(() => `${Math.round(props.cardScale * 100)}%`);

const handleHoverModeSelect = (value: string): void => {
  emit('update:hoverMode', value as HoverMode);
  close();
};

const handleHoverModeReset = (): void => {
  emit('reset:hoverMode');
  close();
};

const handlePageSizeChange = (value: string | number | null): void => {
  if (typeof value === 'number') {
    emit('update:pageSize', value);
  }
};
</script>
