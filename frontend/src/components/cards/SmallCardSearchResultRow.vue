<template>
  <button
    v-if="interactive"
    class="theme-card-frame group relative flex h-16 w-full items-stretch overflow-hidden rounded-xl text-left transition select-none"
    :class="rowClasses"
    type="button"
    :disabled="disabled"
    :aria-label="ariaLabel"
    :aria-selected="selected || undefined"
    @click="handleSelect"
  >
    <CardCompactRowContent
      :card="card"
      art-width="5.5rem"
    />

    <div
      v-if="slots.trailing"
      class="absolute inset-y-0 right-0 z-20 flex items-center px-3"
      @click.stop
    >
      <slot name="trailing" />
    </div>
    <div
      v-else-if="actionLabel"
      class="pointer-events-none absolute inset-y-0 right-0 z-20 flex items-center px-3"
    >
      <span
        class="text-xs font-semibold"
        :class="disabled ? 'theme-section-muted' : 'theme-link'"
      >
        {{ actionLabel }}
      </span>
    </div>
  </button>

  <div
    v-else
    class="theme-card-frame group relative flex h-16 w-full items-stretch overflow-hidden rounded-xl text-left transition select-none"
    :class="rowClasses"
    :aria-label="ariaLabel"
    :aria-selected="selected || undefined"
  >
    <CardCompactRowContent
      :card="card"
      art-width="5.5rem"
    />

    <div
      v-if="slots.trailing"
      class="absolute inset-y-0 right-0 z-20 flex items-center px-3"
      @click.stop
    >
      <slot name="trailing" />
    </div>
    <div
      v-else-if="actionLabel"
      class="pointer-events-none absolute inset-y-0 right-0 z-20 flex items-center px-3"
    >
      <span
        class="text-xs font-semibold"
        :class="disabled ? 'theme-section-muted' : 'theme-link'"
      >
        {{ actionLabel }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue';
import CardCompactRowContent from '@/components/cards/CardCompactRowContent.vue';
import type { CardListItem } from '@/modules/card-detail/types';

const props = withDefaults(defineProps<{
  card: CardListItem;
  disabled?: boolean;
  selected?: boolean;
  actionLabel?: string;
  ariaLabel?: string;
  interactive?: boolean;
}>(), {
  disabled: false,
  selected: false,
  actionLabel: '',
  ariaLabel: undefined,
  interactive: true,
});

const emit = defineEmits<{
  (e: 'activate', card: CardListItem): void;
}>();

const slots = useSlots();
const rowClasses = computed(() => {
  if (props.disabled) {
    return 'cursor-not-allowed opacity-70';
  }
  if (props.selected) {
    return 'theme-selected-surface-strong';
  }
  if (props.interactive) {
    return 'cursor-pointer hover:-translate-y-0.5';
  }
  return 'cursor-default';
});

const handleSelect = (): void => {
  if (!props.interactive || props.disabled) {
    return;
  }
  emit('activate', props.card);
};
</script>
