<template>
  <div
    ref="triggerRef"
    class="group w-full"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <div class="relative transition duration-200 hover:-translate-y-1">
      <RouterLink
        :to="detailLocation"
        class="block"
      >
        <template v-if="isCardGroup">
          <div
            class="relative rounded-2xl"
            :style="{ height: `${cardHeightRem}rem` }"
          >
            <div class="absolute left-1/2 top-0 h-full aspect-[63/88] -translate-x-1/2">
              <div
                class="theme-card-frame-muted absolute inset-0 rounded-2xl"
                :style="{ transform: 'translate(0.45rem, 0.2rem) rotate(5deg)' }"
              />
              <div
                class="theme-card-frame-muted absolute inset-0 rounded-2xl"
                :style="{ transform: 'translate(0.45rem, 0.2rem) rotate(2deg)' }"
              />
              <div class="relative h-full overflow-hidden rounded-2xl">
                <img
                  v-if="stackCards[0]?.image_url"
                  :src="toAbsoluteApiUrl(stackCards[0].image_url)"
                  :alt="stackCards[0].name"
                  class="theme-card-image-well block h-full w-full object-contain transition duration-300 group-hover:scale-[1.02]"
                  loading="lazy"
                  decoding="async"
                >
                <div
                  v-else
                  class="theme-card-image-well theme-section-muted flex h-full items-center justify-center text-sm"
                >
                  No image
                </div>
                <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-950/88 via-slate-950/42 to-transparent p-4">
                  <div class="inline-flex max-w-[85%] flex-col gap-1 rounded-2xl border border-white/14 bg-slate-950/42 px-3 py-2 shadow-lg backdrop-blur-md">
                    <p class="text-sm font-semibold tracking-tight text-white drop-shadow-[0_1px_2px_rgba(15,23,42,0.85)]">
                      {{ groupItem?.group_name }}
                    </p>
                    <p class="text-xs font-medium text-slate-50/95 drop-shadow-[0_1px_2px_rgba(15,23,42,0.8)]">
                      {{ groupItem?.member_count }} cards in this stack
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
        <template v-else>
          <img
            v-if="cardItem?.image_url"
            :src="toAbsoluteApiUrl(cardItem.image_url)"
            alt="Card image"
            class="block w-full object-contain transition duration-300 group-hover:scale-[1.02]"
            :style="{ height: `${cardHeightRem}rem` }"
            loading="lazy"
            decoding="async"
          >
          <div
            v-else
            class="theme-empty-state flex items-center justify-center rounded-xl text-sm"
            :style="{ height: `${cardHeightRem}rem` }"
          >
            No image
          </div>
        </template>
      </RouterLink>

      <Teleport to="body">
        <div
          v-if="tooltipEnabled && hovered && cardItem"
          ref="tooltipRef"
          class="z-30 hidden md:block"
          :style="{ position: 'fixed', left: `${tooltipX}px`, top: `${tooltipY}px` }"
        >
          <CardHoverTooltip :card="cardItem" />
        </div>
      </Teleport>

      <div
        v-if="auth.canAccessStaffRoutes && isCard"
        class="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center p-3 opacity-0 transition duration-200 group-hover:opacity-100"
      >
        <RouterLink
          :to="editLocation"
          class="btn-secondary pointer-events-auto gap-1.5 rounded-full px-3 py-1.5 text-xs shadow-xl"
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
import { toAbsoluteApiUrl } from '@/api/client';
import { Pencil } from 'lucide-vue-next';
import CardHoverTooltip from '@/components/cards/CardHoverTooltip.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import { buildCardDetailLocation, buildGalleryItemLocation } from '@/modules/card-search/galleryNavigation';
import type { CardGroupGalleryItem, CardListItem, GalleryItem } from '@/modules/card-detail/types';

const props = withDefaults(
  defineProps<{
    card: GalleryItem;
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
const isCard = computed((): boolean => props.card.result_type === 'card');
const isCardGroup = computed((): boolean => props.card.result_type === 'card_group');
const cardItem = computed<CardListItem | null>(() => (isCard.value ? props.card as CardListItem : null));
const groupItem = computed<CardGroupGalleryItem | null>(() => (isCardGroup.value ? props.card as CardGroupGalleryItem : null));
const stackCards = computed(() => groupItem.value?.preview_cards.slice(0, 3) ?? []);
const detailLocation = computed(() => buildGalleryItemLocation(props.card, route.query, 'detail'));
const editLocation = computed(() =>
  cardItem.value ? buildCardDetailLocation(cardItem.value.id, route.query, 'edit') : '/cards',
);

</script>
