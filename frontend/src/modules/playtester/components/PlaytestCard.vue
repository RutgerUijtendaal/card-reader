<template>
  <div
    class="playtest-card group relative"
    :class="[
      instance.tapped ? 'playtest-card-tapped' : '',
      compact ? 'playtest-card-compact' : '',
      dragging ? 'playtest-card-drag-source' : '',
      pileMember ? 'playtest-card-pile-member' : '',
      selected ? 'playtest-card-selected' : '',
      middleZoomActive ? 'playtest-card-middle-zoom' : '',
    ]"
    :data-instance-id="instance.instanceId"
    :data-playtest-zone-id="instance.zoneId"
    :data-playtest-pile-group-id="instance.pileGroupId ?? undefined"
    :data-playtest-selected="selected ? 'true' : undefined"
    role="button"
    tabindex="0"
    @click="emit('activate', instance.instanceId)"
    @keydown.enter.prevent="emit('activate', instance.instanceId)"
    @keydown.space.prevent="emit('activate', instance.instanceId)"
    @pointerdown="handlePointerDown"
    @pointerup="endMiddleZoom"
    @pointercancel="endMiddleZoom"
    @pointerleave="endMiddleZoom"
    @auxclick.prevent
    @contextmenu.prevent="emit('context-menu', instance.instanceId, $event)"
    @mouseenter="emit('hover', { type: 'card', instanceId: instance.instanceId })"
    @mouseleave="emit('hover', null)"
  >
    <div class="theme-card-image-well aspect-[63/88] overflow-hidden rounded-xl">
      <img
        v-if="instance.card.image_url"
        :src="toAbsoluteApiUrl(instance.card.image_url)"
        :alt="instance.card.name"
        class="h-full w-full object-contain"
        draggable="false"
      >
      <div
        v-else
        class="theme-empty-state flex h-full items-center justify-center text-xs"
      >
        No image
      </div>
    </div>

    <div
      v-if="showName"
      class="pointer-events-none mt-2"
    >
      <p class="theme-section-title truncate text-xs font-semibold">
        {{ instance.card.name }}
      </p>
    </div>
  </div>

  <Teleport to="body">
    <div
      v-if="middleZoomActive"
      class="playtest-card-zoom-overlay"
      :style="middleZoomStyle"
      data-testid="playtest-card-zoom-overlay"
    >
      <div
        class="playtest-card-zoom-content"
        :class="instance.tapped ? 'playtest-card-zoom-content-tapped' : ''"
      >
        <div class="theme-card-image-well aspect-[63/88] overflow-hidden rounded-xl">
          <img
            v-if="instance.card.image_url"
            :src="toAbsoluteApiUrl(instance.card.image_url)"
            :alt="instance.card.name"
            class="h-full w-full object-contain"
            draggable="false"
          >
          <div
            v-else
            class="theme-empty-state flex h-full items-center justify-center text-xs"
          >
            No image
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';
import type {
  PlaytestCardInstance,
  PlaytestCardSource,
  PlaytestHoverTarget,
} from '@/modules/playtester/types';

const props = withDefaults(
  defineProps<{
    instance: PlaytestCardInstance;
    compact?: boolean;
    dragging?: boolean;
    pileMember?: boolean;
    selected?: boolean;
    showName?: boolean;
  }>(),
  {
    compact: false,
    dragging: false,
    pileMember: false,
    selected: false,
    showName: false,
  },
);

const emit = defineEmits<{
  (e: 'activate', instanceId: string): void;
  (e: 'pointer-card', instanceId: string, source: PlaytestCardSource, event: PointerEvent): void;
  (e: 'context-menu', instanceId: string, event: MouseEvent): void;
  (e: 'hover', target: PlaytestHoverTarget | null): void;
}>();

const middleZoomActive = ref(false);
const middleZoomStyle = ref<Record<string, string>>({});
const MIDDLE_ZOOM_TARGET_WIDTH_REM = 19.5;
const MIDDLE_ZOOM_VIEWPORT_MARGIN_PX = 12;

const clampCenterToViewport = (
  center: number,
  visualSize: number,
  viewportStart: number,
  viewportSize: number,
): number => {
  const minCenter = viewportStart + MIDDLE_ZOOM_VIEWPORT_MARGIN_PX + visualSize / 2;
  const maxCenter = viewportStart + viewportSize - MIDDLE_ZOOM_VIEWPORT_MARGIN_PX - visualSize / 2;
  if (minCenter > maxCenter) {
    return viewportStart + viewportSize / 2;
  }
  return Math.min(Math.max(center, minCenter), maxCenter);
};

const zoomOverlayStyleFromElement = (element: HTMLElement): Record<string, string> => {
  const rect = element.getBoundingClientRect();
  const layoutWidth = element.offsetWidth || rect.width || 1;
  const layoutHeight = element.offsetHeight || rect.height || layoutWidth * (88 / 63);
  const rootFontSize = Number.parseFloat(window.getComputedStyle(document.documentElement).fontSize) || 16;
  const targetSourceWidth = MIDDLE_ZOOM_TARGET_WIDTH_REM * rootFontSize;
  const targetSourceHeight = targetSourceWidth * (layoutHeight / layoutWidth);
  const viewport = window.visualViewport;
  const viewportLeft = viewport?.offsetLeft ?? 0;
  const viewportTop = viewport?.offsetTop ?? 0;
  const viewportWidth = viewport?.width ?? (window.innerWidth || document.documentElement.clientWidth);
  const viewportHeight = viewport?.height ?? (window.innerHeight || document.documentElement.clientHeight);
  const baseVisualWidth = props.instance.tapped ? targetSourceHeight : targetSourceWidth;
  const baseVisualHeight = props.instance.tapped ? targetSourceWidth : targetSourceHeight;
  const maxVisualWidth = Math.max(1, viewportWidth - MIDDLE_ZOOM_VIEWPORT_MARGIN_PX * 2);
  const maxVisualHeight = Math.max(1, viewportHeight - MIDDLE_ZOOM_VIEWPORT_MARGIN_PX * 2);
  const fitScale = Math.min(
    1,
    maxVisualWidth / baseVisualWidth,
    maxVisualHeight / baseVisualHeight,
  );
  const sourceWidth = targetSourceWidth * fitScale;
  const sourceHeight = targetSourceHeight * fitScale;
  const visualWidth = baseVisualWidth * fitScale;
  const visualHeight = baseVisualHeight * fitScale;
  const centerX = clampCenterToViewport(rect.left + rect.width / 2, visualWidth, viewportLeft, viewportWidth);
  const centerY = clampCenterToViewport(rect.top + rect.height / 2, visualHeight, viewportTop, viewportHeight);
  return {
    '--playtest-zoom-source-height': `${sourceHeight}px`,
    '--playtest-zoom-source-width': `${sourceWidth}px`,
    height: `${visualHeight}px`,
    left: `${centerX - visualWidth / 2}px`,
    top: `${centerY - visualHeight / 2}px`,
    width: `${visualWidth}px`,
  };
};

const endMiddleZoom = (): void => {
  middleZoomActive.value = false;
  middleZoomStyle.value = {};
};

const handlePointerDown = (event: PointerEvent): void => {
  if (event.button === 1) {
    event.preventDefault();
    const target = event.currentTarget;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    middleZoomStyle.value = zoomOverlayStyleFromElement(target);
    target.setPointerCapture?.(event.pointerId);
    middleZoomActive.value = true;
    return;
  }
  if (event.button !== 0) {
    return;
  }
  emit('pointer-card', props.instance.instanceId, { type: 'card', zoneId: props.instance.zoneId }, event);
};
</script>

<style scoped>
.playtest-card {
  width: var(--playtest-card-width, 9.75rem);
  cursor: grab;
  touch-action: none;
  user-select: none;
  transition:
    transform 160ms ease,
    opacity 160ms ease,
    filter 160ms ease,
    box-shadow 160ms ease;
  filter: drop-shadow(0 1rem 1.1rem rgba(0, 0, 0, 0.28));
}

.playtest-card:active {
  cursor: grabbing;
}

.playtest-card:hover {
  transform: translateY(-0.18rem);
  filter: drop-shadow(0 1.25rem 1.35rem rgba(0, 0, 0, 0.34));
}

.playtest-card-middle-zoom {
  z-index: 4;
}

.playtest-card-drag-source {
  opacity: 0.22;
  filter: grayscale(0.35) drop-shadow(0 0.3rem 0.4rem rgba(0, 0, 0, 0.16));
}

.playtest-card-selected {
  border-radius: 0.85rem;
  outline: 3px solid color-mix(in srgb, var(--color-accent) 78%, white 22%);
  outline-offset: 0.3rem;
  box-shadow:
    0 0 0 0.38rem color-mix(in srgb, var(--color-accent) 24%, transparent),
    0 0 1.4rem color-mix(in srgb, var(--color-accent) 32%, transparent);
}

.playtest-card-selected::after {
  position: absolute;
  inset: -0.46rem;
  z-index: 6;
  border: 2px solid rgba(255, 255, 255, 0.86);
  border-radius: 1.05rem;
  content: '';
  pointer-events: none;
}

.playtest-card-tapped {
  transform: rotate(90deg);
  opacity: 0.82;
  filter: saturate(0.74) drop-shadow(0 1rem 1.1rem rgba(0, 0, 0, 0.28));
}

.playtest-card-tapped:hover {
  transform: rotate(90deg) translateY(-0.18rem);
}

.playtest-card-compact {
  width: var(--playtest-compact-card-width, 6.25rem);
}

.playtest-card-pile-member {
  filter: drop-shadow(0 0.65rem 0.75rem rgba(0, 0, 0, 0.25));
}

@media (max-width: 767px) {
  .playtest-card {
    width: min(var(--playtest-card-width, 9.75rem), 6.7rem);
  }

  .playtest-card-compact {
    width: min(var(--playtest-compact-card-width, 6.25rem), 4.8rem);
  }
}

.playtest-card-zoom-overlay {
  position: fixed;
  z-index: 2147483647;
  pointer-events: none;
  filter: drop-shadow(0 2rem 2.2rem rgba(0, 0, 0, 0.54));
}

.playtest-card-zoom-content {
  width: 100%;
  height: 100%;
}

.playtest-card-zoom-content-tapped {
  position: absolute;
  top: 50%;
  left: 50%;
  width: var(--playtest-zoom-source-width);
  height: var(--playtest-zoom-source-height);
  transform: translate(-50%, -50%) rotate(90deg);
  transform-origin: center center;
}
</style>
