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
            <div
              v-if="stackCards[2]"
              class="theme-card-frame-muted absolute inset-x-0 top-0 bottom-0 rounded-2xl"
              :style="{ transform: 'translate(1rem, 0.35rem) rotate(7deg)' }"
            />
            <div
              v-if="stackCards[1]"
              class="theme-card-frame-muted absolute inset-x-0 top-0 bottom-0 rounded-2xl"
              :style="{ transform: 'translate(0.45rem, 0.2rem) rotate(3deg)' }"
            />
            <div class="theme-card-frame relative h-full rounded-2xl">
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
              <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-950/78 via-slate-950/35 to-transparent p-4">
                <div class="space-y-1">
                  <p class="text-sm font-semibold text-white">
                    {{ groupItem?.group_name }}
                  </p>
                  <p class="text-xs text-slate-100/90">
                    {{ groupItem?.member_count }} cards in this stack
                  </p>
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
