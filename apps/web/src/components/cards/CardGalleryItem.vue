<template>
  <div
    ref="triggerRef"
    class="group w-full"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <div class="relative transition duration-200 hover:-translate-y-1">
      <RouterLink
        :to="buildDetailLocation(card.id, 'detail')"
        class="block"
      >
        <img
          v-if="card.image_url"
          :src="toAbsoluteApiUrl(card.image_url)"
          alt="Card image"
          class="block w-full object-contain transition duration-300 group-hover:scale-[1.02]"
          :style="{ height: `${cardHeightRem}rem` }"
          loading="lazy"
          decoding="async"
        >
        <div
          v-else
          class="flex items-center justify-center rounded-xl border border-dashed border-slate-300 text-sm text-slate-500"
          :style="{ height: `${cardHeightRem}rem` }"
        >
          No image
        </div>
      </RouterLink>

      <Teleport to="body">
        <div
          v-if="tooltipEnabled && hovered"
          ref="tooltipRef"
          class="z-30 hidden md:block"
          :style="{ position: 'fixed', left: `${tooltipX}px`, top: `${tooltipY}px` }"
        >
          <CardHoverTooltip :card="card" />
        </div>
      </Teleport>

      <div
        v-if="auth.canAccessStaffRoutes"
        class="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center p-3 opacity-0 transition duration-200 group-hover:opacity-100"
      >
        <RouterLink
          :to="buildDetailLocation(card.id, 'edit')"
          class="pointer-events-auto inline-flex items-center gap-1.5 rounded-full border border-slate-900/10 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 shadow-xl transition hover:bg-slate-50"
        >
          <Pencil class="h-3.5 w-3.5" />
          <span>Edit</span>
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from '@floating-ui/vue';
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { api, DEFAULT_API_BASE_URL } from '@/api/client';
import { Pencil } from 'lucide-vue-next';
import CardHoverTooltip from '@/components/cards/CardHoverTooltip.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import { buildCardDetailLocation } from '@/modules/card-search/galleryNavigation';
import type {
  CardHoverTooltipModel,
} from '@/components/cards/cardModels';

export type CardGalleryItemModel = CardHoverTooltipModel & {
  image_url: string | null;
};

withDefaults(
  defineProps<{
    card: CardGalleryItemModel;
    tooltipEnabled?: boolean;
    cardHeightRem?: number;
  }>(),
  {
    tooltipEnabled: true,
    cardHeightRem: 27,
  },
);

const auth = useAuthStore();
const route = useRoute();
const hovered = ref(false);
const triggerRef = ref<HTMLElement | null>(null);
const tooltipRef = ref<HTMLElement | null>(null);
const floating = useFloating(triggerRef, tooltipRef, {
  open: computed(() => hovered.value),
  placement: 'right-start',
  strategy: 'fixed',
  middleware: [offset(16), flip(), shift({ padding: 12 })],
  whileElementsMounted: autoUpdate,
});
const tooltipX = computed(() => floating.x.value ?? 0);
const tooltipY = computed(() => floating.y.value ?? 0);

const buildDetailLocation = (cardId: string, mode: 'detail' | 'edit') =>
  buildCardDetailLocation(cardId, route.query, mode);

const toAbsoluteApiUrl = (urlPath: string): string => {
  const base = api.defaults.baseURL ?? DEFAULT_API_BASE_URL;
  if (urlPath.startsWith('http://') || urlPath.startsWith('https://')) {
    return urlPath;
  }
  return `${base.replace(/\/$/, '')}/${urlPath.replace(/^\//, '')}`;
};
</script>
