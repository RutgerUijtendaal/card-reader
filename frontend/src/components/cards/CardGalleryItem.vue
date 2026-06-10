<template>
  <div
    class="group relative z-0 flex w-full justify-center hover:z-20 focus-within:z-20"
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
          <div class="card-group-stack-root relative h-full w-full rounded-2xl">
            <div
              class="card-group-resting-layers pointer-events-none absolute inset-0 transition duration-200"
              aria-hidden="true"
            >
              <div
                v-for="backCard in restingBackCards"
                :key="`resting-${backCard.card_id}`"
                class="theme-card-frame theme-card-image-well absolute inset-2 overflow-hidden rounded-2xl shadow-xl"
                :class="backCard.side === 'left' ? 'card-group-resting-layer-left' : 'card-group-resting-layer-right'"
                :data-card-group-resting-card-id="backCard.card_id"
              >
                <CardLoadingSkeleton
                  v-if="!backCard.card.image_url"
                  class="absolute inset-0"
                />
                <img
                  v-if="backCard.card.image_url"
                  :src="toAbsoluteApiUrl(backCard.card.image_url)"
                  :alt="backCard.card.name"
                  class="h-full w-full object-contain"
                  loading="lazy"
                  decoding="async"
                >
              </div>
            </div>

            <div
              class="card-group-unfolded-stack pointer-events-none absolute inset-0 opacity-0 transition duration-200"
              aria-hidden="true"
            >
              <div
                v-for="stackCard in stackCards"
                :key="`unfolded-${stackCard.card_id}`"
                class="theme-card-frame theme-card-image-well card-group-unfolded-card absolute inset-0 overflow-hidden rounded-2xl shadow-2xl"
                :style="getUnfoldedCardStyle(stackCard.card_id)"
                :data-card-group-stack-card-id="stackCard.card_id"
                @mouseenter="setHoveredGroupPreviewCard(stackCard.card_id)"
              >
                <CardLoadingSkeleton
                  v-if="!stackCard.image_url"
                  class="absolute inset-0"
                />
                <img
                  v-if="stackCard.image_url"
                  :src="toAbsoluteApiUrl(stackCard.image_url)"
                  :alt="stackCard.name"
                  class="h-full w-full object-contain"
                  loading="lazy"
                  decoding="async"
                >
              </div>
            </div>

            <div
              class="card-group-anchor-card theme-card-image-well relative h-full overflow-hidden rounded-2xl transition duration-200"
              @mouseenter="setHoveredGroupPreviewCard(anchorPreviewCard?.card_id ?? null)"
            >
              <CardLoadingSkeleton
                v-if="!groupImageLoaded || !anchorPreviewCard?.image_url"
                class="absolute inset-0"
              />
              <img
                v-if="anchorPreviewCard?.image_url"
                :src="toAbsoluteApiUrl(anchorPreviewCard.image_url)"
                :alt="anchorPreviewCard.name"
                class="block h-full w-full object-contain transition duration-300"
                :class="groupImageLoaded ? 'opacity-100' : 'opacity-0'"
                loading="lazy"
                decoding="async"
                @load="groupImageLoaded = true"
                @error="groupImageLoaded = true"
              >
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
              v-if="!cardImageLoaded || !cardItem?.image_url"
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
            <span
              v-if="cardIsDeprecated(cardItem)"
              class="theme-pill theme-pill-warning absolute left-3 top-3 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide"
            >
              Deprecated
            </span>
          </div>
        </template>
      </component>

      <Teleport to="body">
        <div
          v-if="sharedElementHover.isMounted.value"
          ref="hoverPanelRef"
          class="pointer-events-none z-30 hidden md:block"
          :class="sharedElementHover.overlayClass.value"
          :style="sharedElementHover.overlayStyle.value"
        >
          <CardHoverTooltip
            v-if="showEnlargedPreview && showDetailsPreview && detailsCard"
            :card="detailsCard"
            :image-url="previewImageUrl"
            :image-alt="previewImageAlt"
            :details-revealed="sharedElementHover.revealDetails.value"
            :hover-preview-scale="hoverPreviewScale"
          />
          <div
            v-else-if="showEnlargedPreview && previewImageUrl"
            class="theme-card-frame overflow-hidden rounded-xl shadow-2xl"
            :style="enlargedPreviewStyle"
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
            :details-revealed="sharedElementHover.revealDetails.value"
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
import { cardIsDeprecated } from '@/composables/card-filters/cardLifecycle';
import { buildCardDetailLocation, buildGalleryItemLocation } from '@/composables/card-gallery/galleryNavigation';
import { DEFAULT_HOVER_MODE, type HoverMode } from '@/composables/card-gallery/hoverMode';
import { normalizeHoverPreviewScale } from '@/composables/card-gallery/hoverPreviewScale';
import { useSharedElementHover } from '@/composables/card-gallery/useSharedElementHover';
import { useHoverModePreferences } from '@/composables/useHoverModePreferences';
import type { CardGroupGalleryItem, CardListItem, GalleryItem } from '@/modules/card-detail/types';
import { blurAfterFinePointerActivation, blurFocusedDescendantAfterFinePointerLeave } from '@/utils/pointerFocus';

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
const BASE_HOVER_CARD_WIDTH_REM = 28;
const route = useRoute();
const { hoverPreviewScale } = useHoverModePreferences();
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
const stackCards = computed(() => groupItem.value?.preview_cards ?? []);
const anchorPreviewCard = computed(() =>
  stackCards.value.find((card) => card.card_id === groupItem.value?.anchor_card_id) ?? stackCards.value[0] ?? null,
);
const restingBackCards = computed(() =>
  stackCards.value
    .filter((card) => card.card_id !== anchorPreviewCard.value?.card_id)
    .slice(0, 2)
    .map((card, index) => ({
      card,
      card_id: card.card_id,
      side: index === 0 ? 'left' : 'right',
    })),
);
const hoveredGroupPreviewCardId = ref<string | null>(null);
const activeGroupPreviewCard = computed(() =>
  stackCards.value.find((card) => card.card_id === hoveredGroupPreviewCardId.value)
  ?? anchorPreviewCard.value,
);
const detailsCard = computed<CardListItem | null>(() => cardItem.value ?? groupHoverCard.value);
const previewCard = computed(() => activeGroupPreviewCard.value);
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
const enlargedPreviewStyle = computed(() => ({
  width: `${Number((BASE_HOVER_CARD_WIDTH_REM * normalizeHoverPreviewScale(hoverPreviewScale.value)).toFixed(3))}rem`,
}));
const sharedElementHover = useSharedElementHover({
  isOpen: showHoverOverlay,
  panelRef: hoverPanelRef,
  triggerRef,
  x: hoverPanelX,
  y: hoverPanelY,
});
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
  hoveredGroupPreviewCardId.value = null;
  blurFocusedDescendantAfterFinePointerLeave(triggerRef.value);
};

const setHoveredGroupPreviewCard = (cardId: string | null): void => {
  hoveredGroupPreviewCardId.value = cardId;
};

const getUnfoldedCardStyle = (cardId: string) => {
  const cardIndex = stackCards.value.findIndex((card) => card.card_id === cardId);
  const safeIndex = cardIndex < 0 ? 0 : cardIndex;
  return {
    '--card-group-stack-index': safeIndex,
    '--card-group-stack-depth': stackCards.value.length - safeIndex - 1,
    zIndex: stackCards.value.length - safeIndex,
  };
};

watch(
  () => cardItem.value?.image_url ?? null,
  () => {
    cardImageLoaded.value = false;
  },
  { immediate: true },
);

watch(
  () => anchorPreviewCard.value?.image_url ?? null,
  () => {
    groupImageLoaded.value = false;
  },
  { immediate: true },
);

watch(
  () => groupItem.value?.anchor_card_id ?? null,
  () => {
    groupHoverCard.value = null;
    hoveredGroupPreviewCardId.value = null;
  },
);

watch(
  [hovered, showDetailsPreview, groupItem, activeGroupPreviewCard],
  async ([isHovered, shouldShowDetails, currentGroup, currentPreviewCard]) => {
    if (!isHovered || !shouldShowDetails || !currentGroup || !currentPreviewCard) {
      return;
    }

    if (groupHoverCard.value?.id === currentPreviewCard.card_id) {
      return;
    }

    const expectedCardId = currentPreviewCard.card_id;
    const loadedCard = await fetchHoverPreviewCard(expectedCardId);
    if (activeGroupPreviewCard.value?.card_id !== expectedCardId) {
      return;
    }
    groupHoverCard.value = loadedCard;
  },
  { immediate: true },
);

</script>

<style scoped>
.card-group-resting-layer-left {
  transform: translate(-0.62rem, -0.16rem) rotate(-6deg);
}

.card-group-resting-layer-right {
  transform: translate(0.62rem, -0.18rem) rotate(6deg);
}

@media (hover: hover) and (pointer: fine) and (min-width: 768px) {
  .card-group-stack-root:hover .card-group-resting-layers,
  .card-group-stack-root:hover .card-group-anchor-card {
    opacity: 0;
    pointer-events: none;
  }

  .card-group-stack-root:hover .card-group-unfolded-stack {
    opacity: 1;
    pointer-events: auto;
  }

  .card-group-unfolded-card {
    transform: translateY(calc(var(--card-group-stack-depth) * 2.05rem));
    transition:
      transform 180ms ease,
      box-shadow 180ms ease;
  }

  .card-group-unfolded-card:hover {
    box-shadow:
      0 22px 45px rgba(15, 23, 42, 0.26),
      0 0 0 2px rgba(255, 255, 255, 0.22);
  }
}
</style>
