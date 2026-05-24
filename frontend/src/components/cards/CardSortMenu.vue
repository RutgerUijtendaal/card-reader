<template>
  <div>
    <button
      ref="triggerRef"
      type="button"
      class="btn-secondary inline-flex items-center gap-1.5 whitespace-nowrap px-3 py-2 text-xs"
      @click="toggle"
    >
      <ArrowUpDown class="h-4 w-4" />
      <span class="font-semibold">Sort</span>
      <span class="theme-section-muted text-[11px] font-medium">
        {{ currentLabel }}
      </span>
    </button>

    <Teleport to="body">
      <div
        v-if="isOpen"
        ref="panelRef"
        class="theme-popover z-30 w-80"
        :style="{ position: 'fixed', left: `${x}px`, top: `${y}px` }"
      >
        <div class="space-y-2">
          <div class="pb-1">
            <p class="theme-section-title text-sm font-semibold">
              Card Sort
            </p>
            <p class="theme-section-muted text-xs">
              Choose how this card list is ordered.
            </p>
          </div>

          <button
            v-if="allowDefaultOption"
            type="button"
            class="theme-card-frame w-full rounded-xl px-3 py-3 text-left transition hover:-translate-y-0.5"
            :class="!overrideActive ? 'theme-selected-surface-strong' : ''"
            @click="handleReset"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="theme-section-title text-sm font-semibold">
                  Use Default
                </p>
                <p class="theme-section-muted mt-1 text-xs">
                  {{ defaultDescription }}
                </p>
              </div>
              <Check
                v-if="!overrideActive"
                class="h-4 w-4 shrink-0"
              />
            </div>
          </button>

          <button
            v-for="option in cardSortOptions"
            :key="option.value"
            type="button"
            class="theme-card-frame w-full rounded-xl px-3 py-3 text-left transition hover:-translate-y-0.5"
            :class="sort === option.value && overrideActive ? 'theme-selected-surface-strong' : ''"
            @click="handleSelect(option.value)"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="theme-section-title text-sm font-semibold">
                  {{ option.label }}
                </p>
                <p class="theme-section-muted mt-1 text-xs">
                  {{ option.description }}
                </p>
              </div>
              <Check
                v-if="sort === option.value && overrideActive"
                class="h-4 w-4 shrink-0"
              />
            </div>
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { ArrowUpDown, Check } from 'lucide-vue-next';
import { useFloatingPopover } from '@/composables/useFloatingPopover';
import { cardSortOptions, getCardSortCompactLabel, getCardSortLabel, type CardSort } from '@/modules/card-search/cardSort';

const props = withDefaults(
  defineProps<{
    sort: CardSort;
    defaultSort: CardSort;
    overrideActive?: boolean;
    allowDefaultOption?: boolean;
  }>(),
  {
    overrideActive: false,
    allowDefaultOption: false,
  },
);

const emit = defineEmits<{
  (e: 'update:sort', value: CardSort): void;
  (e: 'reset'): void;
}>();

const { isOpen, triggerRef, panelRef, x, y, toggle, close } = useFloatingPopover({
  placement: 'bottom-start',
});

const currentLabel = computed(() => getCardSortCompactLabel(props.sort));
const defaultDescription = computed(() => `Follow your global default: ${getCardSortLabel(props.defaultSort)}.`);

const handleSelect = (value: CardSort): void => {
  emit('update:sort', value);
  close();
};

const handleReset = (): void => {
  emit('reset');
  close();
};
</script>
