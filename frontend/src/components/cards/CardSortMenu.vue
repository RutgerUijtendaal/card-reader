<template>
  <div>
    <button
      ref="triggerRef"
      type="button"
      class="btn-secondary inline-flex items-center gap-1.5 whitespace-nowrap px-3 py-2"
      @click="toggle"
    >
      <ArrowUpDown class="h-4 w-4" />
      <span class="font-semibold">Sort</span>
      <span class="theme-section-muted font-medium">
        {{ currentLabel }}
      </span>
    </button>

    <Teleport to="body">
      <div
        v-if="isOpen"
        ref="panelRef"
        class="theme-popover z-30 w-[22rem]"
        :style="{ position: 'fixed', left: `${x}px`, top: `${y}px` }"
      >
        <PopoverOptionList
          title="Card Sort"
          description="Choose how this card list is ordered."
          appearance="list"
          :options="sortOptions"
          :selected-value="sort"
          :selection-active="overrideActive"
          :default-option="allowDefaultOption ? { label: 'Use Global Default', description: defaultDescription } : null"
          @select="handleSelect"
          @reset="handleReset"
        />
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { ArrowUpDown } from 'lucide-vue-next';
import PopoverOptionList, { type PopoverOptionItem } from '@/components/cards/PopoverOptionList.vue';
import { useFloatingPopover } from '@/composables/useFloatingPopover';
import { cardSortOptions, getCardSortCompactLabel, getCardSortLabel, type CardSort } from '@/composables/card-gallery/cardSort';

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
const sortOptions = computed<PopoverOptionItem[]>(() =>
  cardSortOptions.map((option) => ({
    value: option.value,
    label: option.label,
  })),
);
const handleSelect = (value: string): void => {
  emit('update:sort', value as CardSort);
  close();
};

const handleReset = (): void => {
  emit('reset');
  close();
};
</script>
