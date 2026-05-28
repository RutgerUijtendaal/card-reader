<template>
  <div
    class="group flex w-full justify-center"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
  >
    <div
      ref="triggerRef"
      class="relative origin-center"
      :class="isLoadingShim ? '' : 'transition duration-200 hover:-translate-y-1 hover:scale-[1.02]'"
      :style="cardFrameStyle"
    >
      <component
        :is="activationTag"
        v-bind="activationProps"
        class="block w-full bg-transparent p-0 text-left disabled:cursor-not-allowed"
        @click="handleActivate"
      >
        <template v-if="isLoadingShim">
          <CardLoadingSkeleton />
        </template>
        <template v-else-if="isCardGroup">
          <div class="relative h-full w-full rounded-2xl">
            <div
              class="theme-card-frame-muted absolute inset-2 rounded-2xl"
              :style="{ transform: 'translate(0.3rem, -0.0rem) rotate(5deg)' }"
            />
            <div
              class="theme-card-frame-muted absolute inset-2 rounded-2xl"
              :style="{ transform: 'translate(0.1rem, 0.0rem) rotate(2deg)' }"
            />
            <div class="theme-card-image-well relative h-full overflow-hidden rounded-2xl">
              <CardLoadingSkeleton
                v-if="!groupImageLoaded"
                class="absolute inset-0"
              />
              <img
                v-if="stackCards[0]?.image_url"
                :src="toAbsoluteApiUrl(stackCards[0].image_url)"
                :alt="stackCards[0].name"
                class="block h-full w-full object-contain transition duration-300"
                :class="groupImageLoaded ? 'opacity-100' : 'opacity-0'"
                loading="lazy"
                decoding="async"
                @load="groupImageLoaded = true"
                @error="groupImageLoaded = true"
              >
              <div
                v-else
                class="theme-section-muted flex h-full items-center justify-center text-sm"
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
        </template>
        <template v-else>
          <div
            class="theme-card-image-well relative w-full overflow-hidden rounded-2xl"
            :style="{ aspectRatio: DEFAULT_CARD_ASPECT_RATIO }"
          >
            <CardLoadingSkeleton
              v-if="!cardImageLoaded"
              class="absolute inset-0"
            />
            <img
              v-if="cardItem?.image_url"
              :src="toAbsoluteApiUrl(cardItem.image_url)"
              alt="Card image"
              class="absolute inset-0 h-full w-full object-contain transition duration-300"
              :class="cardImageLoaded ? 'opacity-100' : 'opacity-0'"
              loading="lazy"
              decoding="async"
              @load="cardImageLoaded = true"
              @error="cardImageLoaded = true"
            >
            <div
              v-else
              class="theme-empty-state absolute inset-0 flex items-center justify-center rounded-xl text-sm"
            >
              No image
            </div>
          </div>
        </template>
      </component>

      <Teleport to="body">
        <div
          v-if="showHoverOverlay"
          ref="hoverPanelRef"
          class="pointer-events-none z-30 hidden md:block"
          :style="{ position: 'fixed', left: `${hoverPanelX}px`, top: `${hoverPanelY}px` }"
        >
          <CardHoverTooltip
            v-if="showEnlargedPreview && showDetailsPreview && detailsCard"
            :card="detailsCard"
            :image-url="previewImageUrl"
            :image-alt="previewImageAlt"
          />
          <div
            v-else-if="showEnlargedPreview && previewImageUrl"
            class="theme-card-frame w-[28rem] overflow-hidden rounded-xl shadow-2xl"
          >
            <div class="theme-card-image-well aspect-[63/88]">
              <img
                :src="toAbsoluteApiUrl(previewImageUrl)"
                :alt="previewImageAlt"
                class="h-full w-full object-cover"
              >
            </div>
          </div>
          <CardHoverTooltip
            v-else-if="showDetailsPreview && detailsCard"
            :card="detailsCard"
          />
        </div>
      </Teleport>

      <div class="pointer-events-none absolute inset-0">
        <slot name="overlay" />
      </div>

      <div
        v-if="!isLoadingShim"
        class="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center p-3 opacity-0 transition duration-200 group-hover:opacity-100"
      >
        <slot
          name="hover-actions"
          :card-item="cardItem"
          :is-card="isCard"
          :edit-location="editLocation"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from '@floating-ui/vue';
import { computed, ref, watch } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { RouterLink, useRoute } from 'vue-router';
import { toAbsoluteApiUrl } from '@/api/client';
import { fetchHoverPreviewCard } from '@/components/cards/cardHoverPreview';
import type { GalleryDisplayItem } from '@/components/cards/galleryDisplayItems';
import CardHoverTooltip from '@/components/cards/CardHoverTooltip.vue';
import CardLoadingSkeleton from '@/components/cards/CardLoadingSkeleton.vue';
import { buildCardDetailLocation, buildGalleryItemLocation } from '@/modules/card-search/galleryNavigation';
import { DEFAULT_HOVER_MODE, type HoverMode } from '@/modules/card-search/hoverMode';
import type { CardGroupGalleryItem, CardListItem, GalleryItem } from '@/modules/card-detail/types';
import { blurAfterFinePointerActivation } from '@/utils/pointerFocus';

const props = withDefaults(
  defineProps<{
    card: GalleryDisplayItem;
    hoverMode?: HoverMode;
    cardHeightRem?: number;
    activationMode?: 'navigate' | 'emit';
    activationLabel?: string;
    navigationTarget?: RouteLocationRaw | null;
    activationDisabled?: boolean;
  }>(),
  {
    hoverMode: DEFAULT_HOVER_MODE,
    cardHeightRem: 27,
    activationMode: 'navigate',
    activationLabel: 'Open card',
    navigationTarget: null,
    activationDisabled: false,
  },
);
const emit = defineEmits<{
  (e: 'activate', card: GalleryItem): void;
}>();

const DEFAULT_CARD_ASPECT_RATIO = '63 / 88';
const route = useRoute();
const hovered = ref(false);
const triggerRef = ref<HTMLElement | null>(null);
const hoverPanelRef = ref<HTMLElement | null>(null);
const groupHoverCard = ref<CardListItem | null>(null);
const cardImageLoaded = ref(false);
const groupImageLoaded = ref(false);
const isLoadingShim = computed((): boolean => props.card.result_type === 'loading_shim');
const isCard = computed((): boolean => props.card.result_type === 'card');
const isCardGroup = computed((): boolean => props.card.result_type === 'card_group');
const cardItem = computed<CardListItem | null>(() => (isCard.value ? props.card as CardListItem : null));
const groupItem = computed<CardGroupGalleryItem | null>(() => (isCardGroup.value ? props.card as CardGroupGalleryItem : null));
const stackCards = computed(() => groupItem.value?.preview_cards.slice(0, 3) ?? []);
const detailsCard = computed<CardListItem | null>(() => cardItem.value ?? groupHoverCard.value);
const previewCard = computed(() => stackCards.value[0] ?? null);
const previewImageUrl = computed(() => cardItem.value?.image_url ?? previewCard.value?.image_url ?? null);
const previewImageAlt = computed(() => cardItem.value?.name ?? previewCard.value?.name ?? groupItem.value?.anchor_card_name ?? 'Card preview');
const showEnlargedPreview = computed(() => props.hoverMode === 'enlarged' || props.hoverMode === 'enlarged-details');
const showDetailsPreview = computed(() => props.hoverMode === 'details' || props.hoverMode === 'enlarged-details');
const showHoverOverlay = computed(() => {
  if (!hovered.value || props.hoverMode === 'none' || isLoadingShim.value) {
    return false;
  }

  return (showEnlargedPreview.value && previewImageUrl.value !== null)
    || (showDetailsPreview.value && detailsCard.value !== null);
});
const floating = useFloating(triggerRef, hoverPanelRef, {
  open: showHoverOverlay,
  placement: 'right-start',
  strategy: 'fixed',
  middleware: [offset(16), flip(), shift({ padding: 12 })],
  whileElementsMounted: autoUpdate,
});
const hoverPanelX = computed(() => floating.x.value ?? 0);
const hoverPanelY = computed(() => floating.y.value ?? 0);
const cardFrameWidthRem = computed(() => Number(((props.cardHeightRem * 63) / 88).toFixed(3)));
const cardFrameStyle = computed(() =>
  isCardGroup.value
    ? {
        height: `${props.cardHeightRem}rem`,
        width: `${cardFrameWidthRem.value}rem`,
        maxWidth: '100%',
      }
    : {
        width: `${cardFrameWidthRem.value}rem`,
        maxWidth: '100%',
      },
);
const detailLocation = computed<RouteLocationRaw>(() =>
  isLoadingShim.value ? '/cards' : buildGalleryItemLocation(props.card as GalleryItem, route.query, 'detail'),
);
const editLocation = computed(() =>
  cardItem.value ? buildCardDetailLocation(cardItem.value.id, route.query, 'edit') : '/cards',
);
const navigationTarget = computed<RouteLocationRaw>(() => props.navigationTarget ?? detailLocation.value);
const activationTag = computed(() => {
  if (isLoadingShim.value) {
    return 'div';
  }
  return props.activationMode === 'emit' ? 'button' : RouterLink;
});
const activationProps = computed(() =>
  isLoadingShim.value
    ? {}
    : props.activationMode === 'emit'
    ? {
        type: 'button',
        'aria-label': props.activationLabel,
        disabled: props.activationDisabled,
      }
    : {
        to: navigationTarget.value,
      },
);

const handleActivate = (event: MouseEvent): void => {
  if (isLoadingShim.value) {
    return;
  }
  if (props.activationMode === 'emit' && !props.activationDisabled) {
    emit('activate', props.card as GalleryItem);
    blurAfterFinePointerActivation(event);
  }
};

const handleMouseEnter = (): void => {
  if (isLoadingShim.value) {
    return;
  }
  hovered.value = true;
};

const handleMouseLeave = (): void => {
  hovered.value = false;
};

watch(
  () => cardItem.value?.image_url ?? null,
  () => {
    cardImageLoaded.value = false;
  },
  { immediate: true },
);

watch(
  () => stackCards.value[0]?.image_url ?? null,
  () => {
    groupImageLoaded.value = false;
  },
  { immediate: true },
);

watch(
  () => groupItem.value?.anchor_card_id ?? null,
  () => {
    groupHoverCard.value = null;
  },
);

watch(
  [hovered, showDetailsPreview, groupItem],
  async ([isHovered, shouldShowDetails, currentGroup]) => {
    if (!isHovered || !shouldShowDetails || !currentGroup) {
      return;
    }

    if (groupHoverCard.value?.id === currentGroup.anchor_card_id) {
      return;
    }

    const expectedAnchorId = currentGroup.anchor_card_id;
    const loadedCard = await fetchHoverPreviewCard(expectedAnchorId);
    if (groupItem.value?.anchor_card_id !== expectedAnchorId) {
      return;
    }
    groupHoverCard.value = loadedCard;
  },
  { immediate: true },
);

</script>
