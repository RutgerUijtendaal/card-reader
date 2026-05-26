<template>
  <div
    ref="triggerRef"
    class="theme-card-frame group flex items-center gap-3 rounded-2xl px-3 py-2"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <div class="min-w-0 flex-1">
      <p class="theme-section-title truncate text-sm font-semibold">
        {{ entry.card.name }}
      </p>
    </div>

    <div class="flex items-center gap-2">
      <button
        class="btn-secondary h-8 w-8 px-0"
        type="button"
        @click="$emit('decrement', entry.card.id)"
      >
        -
      </button>
      <input
        :value="entry.quantity"
        class="input-base h-8 w-12 px-1 text-center text-sm"
        type="number"
        min="1"
        :max="quantityMax"
        @input="$emit('setQuantity', entry.card.id, ($event.target as HTMLInputElement).value)"
      >
      <button
        class="btn-secondary h-8 w-8 px-0"
        type="button"
        :disabled="quantityMax !== undefined && entry.quantity >= quantityMax"
        @click="$emit('increment', entry.card.id)"
      >
        +
      </button>
    </div>

    <button
      class="theme-section-muted shrink-0 px-1 text-base font-semibold transition hover:text-rose-300"
      type="button"
      aria-label="Remove card from board"
      @click="$emit('remove', entry.card.id)"
    >
      X
    </button>

    <Teleport to="body">
      <div
        v-if="showHoverOverlay"
        ref="hoverPanelRef"
        class="pointer-events-none z-30 hidden md:block"
        :style="{ position: 'fixed', left: `${hoverPanelX}px`, top: `${hoverPanelY}px` }"
      >
        <CardHoverTooltip
          v-if="showEnlargedPreview && showDetailsPreview"
          :card="entry.card"
          :image-url="entry.card.image_url"
          :image-alt="entry.card.name"
        />
        <div
          v-else-if="showEnlargedPreview && entry.card.image_url"
          class="theme-card-frame w-[28rem] overflow-hidden rounded-xl shadow-2xl"
        >
          <div class="theme-card-image-well aspect-[63/88]">
            <img
              :src="toAbsoluteApiUrl(entry.card.image_url)"
              :alt="entry.card.name"
              class="h-full w-full object-cover"
            >
          </div>
        </div>
        <CardHoverTooltip
          v-else-if="showDetailsPreview"
          :card="entry.card"
        />
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from '@floating-ui/vue';
import { computed, ref } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';
import CardHoverTooltip from '@/components/cards/CardHoverTooltip.vue';
import type { HoverMode } from '@/modules/card-search/hoverMode';
import type { DeckEntrySummary } from '@/modules/decks/types';

const props = defineProps<{
  entry: DeckEntrySummary;
  hoverMode: HoverMode;
  quantityMax?: number;
}>();

defineEmits<{
  (e: 'decrement', cardId: string): void;
  (e: 'increment', cardId: string): void;
  (e: 'setQuantity', cardId: string, value: string): void;
  (e: 'remove', cardId: string): void;
}>();

const hovered = ref(false);
const triggerRef = ref<HTMLElement | null>(null);
const hoverPanelRef = ref<HTMLElement | null>(null);
const showEnlargedPreview = computed(() => props.hoverMode === 'enlarged' || props.hoverMode === 'enlarged-details');
const showDetailsPreview = computed(() => props.hoverMode === 'details' || props.hoverMode === 'enlarged-details');
const showHoverOverlay = computed(() => {
  if (!hovered.value || props.hoverMode === 'none') {
    return false;
  }

  return (showEnlargedPreview.value && props.entry.card.image_url !== null) || showDetailsPreview.value;
});
const floating = useFloating(triggerRef, hoverPanelRef, {
  open: showHoverOverlay,
  placement: 'left-start',
  strategy: 'fixed',
  middleware: [offset(16), flip(), shift({ padding: 12 })],
  whileElementsMounted: autoUpdate,
});
const hoverPanelX = computed(() => floating.x.value ?? 0);
const hoverPanelY = computed(() => floating.y.value ?? 0);
</script>
