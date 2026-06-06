<template>
  <div
    v-if="cards.length > 0"
    class="flex flex-wrap gap-2"
  >
    <RouterLink
      v-for="card in cards"
      :key="card.card_version_id"
      :to="detailLocation(card.card_id)"
      class="theme-card-frame group w-[210px] rounded-lg transition duration-200 hover:-translate-y-0.5"
      :title="`${card.card_label} (${card.card_version_name})`"
      @mouseenter="showHoverPreview(card, $event)"
      @mouseleave="hideHoverPreview"
    >
      <div class="theme-card-image-well aspect-[0.72]">
        <img
          v-if="card.image_url"
          :src="toAbsoluteApiUrl(card.image_url)"
          :alt="card.card_label"
          class="h-full w-full object-cover"
          loading="lazy"
        >
        <div
          v-else
          class="theme-kicker flex h-full items-center justify-center text-xs font-semibold uppercase tracking-[0.16em]"
        >
          No image
        </div>
      </div>
    </RouterLink>
  </div>

  <div
    v-else
    class="theme-empty-state px-3 py-6 text-center"
  >
    {{ emptyMessage }}
  </div>

  <Teleport to="body">
    <div
      v-if="hoverPreview"
      ref="hoverPanelRef"
      class="pointer-events-none fixed left-0 top-0 z-[1200]"
      :style="{ left: `${hoverPreviewX}px`, top: `${hoverPreviewY}px` }"
    >
      <div class="theme-card-frame w-[320px] rounded-xl shadow-2xl">
        <div class="theme-card-image-well aspect-[0.72]">
          <img
            :src="toAbsoluteApiUrl(hoverPreview.image_url!)"
            :alt="hoverPreview.card_label"
            class="h-full w-full object-cover"
          >
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from '@floating-ui/vue';
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { toAbsoluteApiUrl } from '@/api/client';
import { buildAdminCardDetailLocation } from '@/composables/admin/adminRouteState';
import type { LinkedCardPreview } from '@/modules/admin/types';

defineProps<{
  cards: LinkedCardPreview[];
  emptyMessage: string;
}>();

const hoverPreview = ref<LinkedCardPreview | null>(null);
const route = useRoute();
const hoverTriggerRef = ref<HTMLElement | null>(null);
const hoverPanelRef = ref<HTMLElement | null>(null);
const floating = useFloating(hoverTriggerRef, hoverPanelRef, {
  open: computed(() => hoverPreview.value !== null),
  placement: 'right-start',
  strategy: 'fixed',
  middleware: [offset(16), flip(), shift({ padding: 12 })],
  whileElementsMounted: autoUpdate,
});
const hoverPreviewX = computed(() => floating.x.value ?? 0);
const hoverPreviewY = computed(() => floating.y.value ?? 0);

const detailLocation = (cardId: string) => buildAdminCardDetailLocation(cardId, route.query);

const showHoverPreview = (card: LinkedCardPreview, event: MouseEvent): void => {
  if (!card.image_url) {
    hoverPreview.value = null;
    hoverTriggerRef.value = null;
    return;
  }
  hoverPreview.value = card;
  hoverTriggerRef.value = event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
};

const hideHoverPreview = (): void => {
  hoverPreview.value = null;
  hoverTriggerRef.value = null;
};
</script>
