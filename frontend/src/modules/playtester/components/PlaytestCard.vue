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
import { getCardZoomOverlayStyle } from '@/modules/playtester/utils/zoom';

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
    middleZoomStyle.value = getCardZoomOverlayStyle(target, props.instance.tapped);
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
