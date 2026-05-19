<template>
  <div
    v-if="cards.length > 0"
    class="flex flex-wrap gap-2"
  >
    <RouterLink
      v-for="card in cards"
      :key="card.card_version_id"
      :to="detailLocation(card.card_id)"
      class="group w-[210px] overflow-hidden rounded-lg border border-slate-200 bg-white transition duration-200 hover:border-slate-300 hover:shadow-sm"
      :title="`${card.card_label} (${card.card_version_name})`"
      @mouseenter="showHoverPreview(card, $event)"
      @mouseleave="hideHoverPreview"
    >
      <div class="aspect-[0.72] bg-slate-100">
        <img
          v-if="card.image_url"
          :src="toAbsoluteApiUrl(card.image_url)"
          :alt="card.card_label"
          class="h-full w-full object-cover"
          loading="lazy"
        >
        <div
          v-else
          class="flex h-full items-center justify-center text-xs font-semibold uppercase tracking-[0.16em] text-slate-400"
        >
          No image
        </div>
      </div>
    </RouterLink>
  </div>

  <div
    v-else
    class="rounded-lg border border-dashed border-slate-300 bg-white px-3 py-6 text-center text-sm text-slate-500"
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
      <div class="w-[320px] overflow-hidden rounded-xl border border-slate-300 bg-white shadow-2xl">
        <div class="aspect-[0.72] bg-slate-100">
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
import { DEFAULT_API_BASE_URL } from '@/api/client';
import { buildSettingsCardDetailLocation } from '@/modules/settings/settingsRouteState';
import type { LinkedCardPreview } from '@/modules/settings/types';

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

const toAbsoluteApiUrl = (urlPath: string): string => new URL(urlPath, DEFAULT_API_BASE_URL).toString();
const detailLocation = (cardId: string) => buildSettingsCardDetailLocation(cardId, route.query);

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
