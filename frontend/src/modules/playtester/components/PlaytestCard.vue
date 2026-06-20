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
      interactive ? 'playtest-card-interactive' : 'playtest-card-static',
    ]"
    :data-instance-id="instance.instanceId"
    :data-playtest-zone-id="instance.zoneId"
    :data-playtest-setup-origin="instance.setupOrigin ? 'true' : undefined"
    :data-playtest-pile-group-id="instance.pileGroupId ?? undefined"
    :data-playtest-selected="selected ? 'true' : undefined"
    :role="canActivate ? 'button' : undefined"
    :tabindex="canActivate ? 0 : undefined"
    @click="activateCard"
    @keydown.enter.prevent="activateCard"
    @keydown.space.prevent="activateCard"
    @pointerdown="handlePointerDown"
    @pointerup="endMiddleZoom"
    @pointercancel="endMiddleZoom"
    @pointerleave="endMiddleZoom"
    @auxclick.prevent
    @contextmenu="openContextMenu"
    @mouseenter="setHoveredCard"
    @mouseleave="clearHoveredCard"
  >
    <div
      class="playtest-card-image-frame theme-card-image-well aspect-[63/88] overflow-hidden rounded-xl"
      :class="faceAnimationActive ? 'playtest-card-face-animating' : ''"
    >
      <img
        v-if="instance.face === 'front' && instance.card.image_url"
        :src="toAbsoluteApiUrl(instance.card.image_url)"
        :alt="instance.card.name"
        class="h-full w-full object-contain"
        draggable="false"
      >
      <div
        v-else-if="instance.face === 'front'"
        class="theme-empty-state flex h-full items-center justify-center text-xs"
      >
        No image
      </div>
      <img
        v-else-if="cardBackUrl"
        :src="cardBackUrl"
        :alt="`${instance.card.name} face down`"
        class="h-full w-full object-contain"
        draggable="false"
      >
      <span
        v-else
        class="playtest-card-back"
        aria-hidden="true"
      />
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
            v-if="instance.face === 'front' && instance.card.image_url"
            :src="toAbsoluteApiUrl(instance.card.image_url)"
            :alt="instance.card.name"
            class="h-full w-full object-contain"
            draggable="false"
          >
          <div
            v-else-if="instance.face === 'front'"
            class="theme-empty-state flex h-full items-center justify-center text-xs"
          >
            No image
          </div>
          <img
            v-else-if="cardBackUrl"
            :src="cardBackUrl"
            :alt="`${instance.card.name} face down`"
            class="h-full w-full object-contain"
            draggable="false"
          >
          <span
            v-else
            class="playtest-card-back"
            aria-hidden="true"
          />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';
import type {
  PlaytestCardInstance,
  PlaytestCardSource,
  PlaytestHoverTarget,
} from '@/modules/playtester/types';
import { getCardZoomOverlayStyle } from '@/modules/playtester/utils/zoom';

const props = withDefaults(
  defineProps<{
    instance: PlaytestCardInstance;
    compact?: boolean;
    activatable?: boolean;
    dragging?: boolean;
    interactive?: boolean;
    pileMember?: boolean;
    selected?: boolean;
    showName?: boolean;
    cardBackUrl?: string | null;
  }>(),
  {
    compact: false,
    activatable: true,
    dragging: false,
    interactive: true,
    pileMember: false,
    selected: false,
    showName: false,
    cardBackUrl: null,
  },
);

const emit = defineEmits<{
  (e: 'activate', instanceId: string, event: MouseEvent | KeyboardEvent): void;
  (e: 'pointer-card', instanceId: string, source: PlaytestCardSource, event: PointerEvent): void;
  (e: 'context-menu', instanceId: string, event: MouseEvent): void;
  (e: 'hover', target: PlaytestHoverTarget | null): void;
}>();

const middleZoomActive = ref(false);
const middleZoomStyle = ref<Record<string, string>>({});
const faceAnimationActive = ref(false);
const canActivate = computed(() => props.interactive && props.activatable);
let faceAnimationTimer: number | null = null;

const endMiddleZoom = (): void => {
  middleZoomActive.value = false;
  middleZoomStyle.value = {};
};

const activateCard = (event: MouseEvent | KeyboardEvent): void => {
  if (!canActivate.value) {
    return;
  }
  emit('activate', props.instance.instanceId, event);
};

const openContextMenu = (event: MouseEvent): void => {
  if (!props.interactive) {
    return;
  }
  event.preventDefault();
  emit('context-menu', props.instance.instanceId, event);
};

const setHoveredCard = (): void => {
  if (!props.interactive) {
    return;
  }
  emit('hover', { type: 'card', instanceId: props.instance.instanceId });
};

const clearHoveredCard = (): void => {
  if (!props.interactive) {
    return;
  }
  emit('hover', null);
};

const handlePointerDown = (event: PointerEvent): void => {
  if (event.button === 1) {
    event.preventDefault();
    const target = event.currentTarget;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    middleZoomStyle.value = getCardZoomOverlayStyle(target, props.instance.tapped);
    target.setPointerCapture?.(event.pointerId);
    middleZoomActive.value = true;
    return;
  }
  if (event.button !== 0) {
    return;
  }
  if (!props.interactive) {
    return;
  }
  emit('pointer-card', props.instance.instanceId, { type: 'card', zoneId: props.instance.zoneId }, event);
};

watch(
  () => props.instance.face,
  (face, previousFace) => {
    if (face === previousFace) {
      return;
    }
    faceAnimationActive.value = true;
    if (faceAnimationTimer) {
      window.clearTimeout(faceAnimationTimer);
    }
    faceAnimationTimer = window.setTimeout(() => {
      faceAnimationActive.value = false;
      faceAnimationTimer = null;
    }, 180);
  },
);

onBeforeUnmount(() => {
  if (faceAnimationTimer) {
    window.clearTimeout(faceAnimationTimer);
  }
});
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

.playtest-card-static {
  cursor: default;
  touch-action: auto;
}

.playtest-card:hover {
  transform: translateY(-0.18rem);
  filter: drop-shadow(0 1.25rem 1.35rem rgba(0, 0, 0, 0.34));
}

.playtest-card-image-frame {
  transform-origin: center center;
}

.playtest-card-face-animating {
  animation: playtest-card-face-flip 180ms ease-out;
}

.playtest-card-back {
  display: block;
  width: 100%;
  height: 100%;
  background:
    radial-gradient(circle at 50% 46%, rgba(245, 158, 11, 0.75), transparent 18%),
    radial-gradient(circle at 34% 35%, rgba(59, 130, 246, 0.7), transparent 12%),
    radial-gradient(circle at 65% 60%, rgba(239, 68, 68, 0.62), transparent 14%),
    linear-gradient(145deg, #5c3516, #92622d 46%, #3d2412);
}

.playtest-card-middle-zoom {
  z-index: 4;
}

.playtest-card-drag-source {
  opacity: 0.22;
  filter: grayscale(0.35) drop-shadow(0 0.3rem 0.4rem rgba(0, 0, 0, 0.16));
  transition: none;
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

@keyframes playtest-card-face-flip {
  0% {
    opacity: 0.86;
    transform: rotateY(84deg);
  }

  100% {
    opacity: 1;
    transform: rotateY(0deg);
  }
}
</style>
