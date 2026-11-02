<template>
  <Teleport to="body">
    <div
      v-if="sharedElementHover.isMounted.value"
      ref="hoverPanelRef"
      class="pointer-events-none z-30 hidden md:block"
      :class="sharedElementHover.overlayClass.value"
      :style="sharedElementHover.overlayStyle.value"
    >
      <CardHoverTooltip
        v-if="showEnlargedPreview && showDetailsPreview"
        :card="card"
        :image-url="card.image_url"
        :image-alt="card.name"
        :details-revealed="sharedElementHover.revealDetails.value"
        :hover-preview-scale="hoverPreviewScale"
      />
      <div
        v-else-if="showEnlargedPreview && card.image_url"
        class="theme-card-frame overflow-hidden rounded-xl shadow-2xl"
        :style="enlargedPreviewStyle"
      >
        <div class="theme-card-image-well aspect-[63/88]">
          <img
            :src="toAbsoluteApiUrl(card.image_url)"
            :alt="card.name"
            class="h-full w-full object-cover"
          >
        </div>
      </div>
      <CardHoverTooltip
        v-else-if="showDetailsPreview"
        :card="card"
        :details-revealed="sharedElementHover.revealDetails.value"
      />
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating, type Placement } from '@floating-ui/vue';
import { computed, ref, toRef } from 'vue';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import CardHoverTooltip from '@/domain/cards/components/CardHoverTooltip.vue';
import type { CardListItem } from '@/domain/cards/types';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';
import { getHoverPreviewCardWidthRem } from '@/domain/cards/utils/gallery/hoverPreviewScale';
import { useSharedElementHover } from '@/domain/cards/composables/useSharedElementHover';
import { useHoverModePreferences } from '@/domain/cards/composables/useHoverModePreferences';

/**
 * The hover preview for a compact card row: an enlarged image, the details panel, or both,
 * following the surface's hover mode and anchored beside the row.
 */
const props = withDefaults(
  defineProps<{
    anchor: HTMLElement | null;
    card: CardListItem;
    hoverMode: HoverMode;
    active: boolean;
    placement?: Placement;
  }>(),
  { placement: 'left-start' },
);

const triggerRef = toRef(props, 'anchor');
const hoverPanelRef = ref<HTMLElement | null>(null);
const { hoverPreviewScale } = useHoverModePreferences();
const showEnlargedPreview = computed(
  () => props.hoverMode === 'enlarged' || props.hoverMode === 'enlarged-details',
);
const showDetailsPreview = computed(
  () => props.hoverMode === 'details' || props.hoverMode === 'enlarged-details',
);
const showHoverOverlay = computed(() => {
  if (!props.active || props.hoverMode === 'none') {
    return false;
  }
  return (showEnlargedPreview.value && props.card.image_url !== null) || showDetailsPreview.value;
});
const floating = useFloating(triggerRef, hoverPanelRef, {
  open: showHoverOverlay,
  placement: toRef(props, 'placement'),
  strategy: 'fixed',
  middleware: [offset(16), flip(), shift({ padding: 12 })],
  whileElementsMounted: autoUpdate,
});
const hoverPanelX = computed(() => floating.x.value ?? 0);
const hoverPanelY = computed(() => floating.y.value ?? 0);
const enlargedPreviewStyle = computed(() => ({
  width: `${getHoverPreviewCardWidthRem(hoverPreviewScale.value)}rem`,
}));
const sharedElementHover = useSharedElementHover({
  isOpen: showHoverOverlay,
  panelRef: hoverPanelRef,
  triggerRef,
  x: hoverPanelX,
  y: hoverPanelY,
});
</script>
