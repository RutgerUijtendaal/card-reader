<template>
  <div
    class="playtest-stack"
    :class="[
      instances.length === 0 ? 'playtest-stack-empty' : '',
      collapsed ? 'playtest-stack-collapsed' : '',
      draggingTop ? 'playtest-stack-dragging-top' : '',
      shuffling ? 'playtest-stack-shuffling' : '',
      interactive ? '' : 'playtest-stack-passive',
      draggable ? '' : 'playtest-stack-open-only',
    ]"
    :data-testid="`playtest-${zoneId}-zone`"
    :data-playtest-stack-zone-id="zoneId"
    :role="interactive ? 'button' : undefined"
    :tabindex="interactive ? 0 : undefined"
    @click="runDefaultAction"
    @keydown.enter.prevent="runDefaultAction"
    @keydown.space.prevent="runDefaultAction"
    @pointerdown="handlePointerDown"
    @pointerup="endMiddleZoom"
    @pointercancel="endMiddleZoom"
    @pointerleave="endMiddleZoom"
    @auxclick.prevent
    @contextmenu="openContextMenu"
    @mouseenter="setHoveredStack"
    @mouseleave="clearHoveredStack"
  >
    <div class="playtest-stack-header">
      <span class="playtest-stack-title">{{ label }}</span>
      <span class="playtest-stack-count">{{ instances.length }}</span>
    </div>

    <div class="playtest-stack-preview">
      <template v-if="instances.length > 0">
        <div class="playtest-stack-shadow playtest-stack-shadow-one" />
        <div class="playtest-stack-shadow playtest-stack-shadow-two" />
        <div
          ref="topCardRef"
          class="playtest-stack-card"
        >
          <img
            v-if="showTopFace && topInstance?.card.image_url"
            :src="toAbsoluteApiUrl(topInstance.card.image_url)"
            :alt="topInstance.card.name"
            draggable="false"
          >
          <div
            v-else-if="showTopFace"
            class="playtest-stack-no-image"
          >
            {{ topInstance?.card.name ?? 'No cards' }}
          </div>
          <img
            v-else-if="cardBackUrl"
            :src="cardBackUrl"
            :alt="`${label} card back`"
            draggable="false"
          >
          <span
            v-else
            class="playtest-stack-card-back"
            aria-hidden="true"
          />
        </div>
      </template>
      <span
        v-else
        class="playtest-stack-empty-label"
      >
        No cards
      </span>
    </div>
  </div>

  <Teleport to="body">
    <div
      v-if="middleZoomActive && topInstance"
      class="playtest-stack-zoom-overlay"
      :style="middleZoomStyle"
      data-testid="playtest-stack-zoom-overlay"
    >
      <div class="playtest-stack-zoom-content">
        <div class="playtest-stack-zoom-card">
          <img
            v-if="showTopFace && topInstance.card.image_url"
            :src="toAbsoluteApiUrl(topInstance.card.image_url)"
            :alt="topInstance.card.name"
            draggable="false"
          >
          <div
            v-else-if="showTopFace"
            class="playtest-stack-zoom-no-image"
          >
            {{ topInstance.card.name }}
          </div>
          <img
            v-else-if="cardBackUrl"
            :src="cardBackUrl"
            :alt="`${label} top card`"
            draggable="false"
          >
          <span
            v-else
            class="playtest-stack-card-back"
            aria-hidden="true"
          />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';
import type {
  PlaytestCardInstance,
  PlaytestHoverTarget,
  PlaytestStackDefaultAction,
  PlaytestStackFace,
  PlaytestZoneId,
} from '@/modules/playtester/types';
import { getCardZoomOverlayStyle } from '@/modules/playtester/utils/zoom';

const props = withDefaults(defineProps<{
  zoneId: PlaytestZoneId;
  label: string;
  instances: PlaytestCardInstance[];
  face: PlaytestStackFace;
  cardBackUrl: string | null;
  collapsed: boolean;
  defaultAction: PlaytestStackDefaultAction;
  draggingTop: boolean;
  shuffling?: boolean;
  interactive?: boolean;
  draggable?: boolean;
}>(), {
  draggable: true,
  interactive: true,
  shuffling: false,
});

const emit = defineEmits<{
  (e: 'open', zoneId: PlaytestZoneId): void;
  (e: 'draw', zoneId: PlaytestZoneId): void;
  (e: 'pointer-top', zoneId: PlaytestZoneId, instanceId: string, event: PointerEvent): void;
  (e: 'context-menu', zoneId: PlaytestZoneId, event: MouseEvent): void;
  (e: 'hover', target: PlaytestHoverTarget | null): void;
}>();

const topInstance = computed(() =>
  props.zoneId === 'library' ? props.instances[0] : props.instances[props.instances.length - 1],
);
const showTopFace = computed(() => props.face === 'front' && topInstance.value?.face !== 'back');
const middleZoomActive = ref(false);
const middleZoomStyle = ref<Record<string, string>>({});
const topCardRef = ref<HTMLElement | null>(null);

const endMiddleZoom = (): void => {
  middleZoomActive.value = false;
  middleZoomStyle.value = {};
};

const runDefaultAction = (): void => {
  if (!props.interactive) {
    return;
  }
  if (props.instances.length === 0) {
    return;
  }
  if (props.defaultAction === 'draw') {
    emit('draw', props.zoneId);
  } else {
    emit('open', props.zoneId);
  }
};

const handlePointerDown = (event: PointerEvent): void => {
  if (event.button === 1) {
    const instance = topInstance.value;
    if (!instance) {
      return;
    }
    event.preventDefault();
    const target = topCardRef.value;
    if (!target) {
      return;
    }
    middleZoomStyle.value = getCardZoomOverlayStyle(target, false);
    if (event.currentTarget instanceof HTMLElement) {
      event.currentTarget.setPointerCapture?.(event.pointerId);
    }
    middleZoomActive.value = true;
    return;
  }
  if (!props.interactive) {
    return;
  }
  if (!props.draggable) {
    return;
  }
  if (event.button !== 0) {
    return;
  }
  const instance = topInstance.value;
  if (!instance) {
    return;
  }
  emit('pointer-top', props.zoneId, instance.instanceId, event);
};

const openContextMenu = (event: MouseEvent): void => {
  if (!props.interactive) {
    return;
  }
  event.preventDefault();
  emit('context-menu', props.zoneId, event);
};

const setHoveredStack = (): void => {
  if (!props.interactive) {
    return;
  }
  emit('hover', { type: 'stack', zoneId: props.zoneId });
};

const clearHoveredStack = (): void => {
  if (!props.interactive) {
    return;
  }
  emit('hover', null);
};

onBeforeUnmount(() => {
  endMiddleZoom();
});
</script>

<style scoped>
.playtest-stack {
  position: relative;
  width: var(--playtest-stack-full-width, 11.35rem);
  min-height: calc(var(--playtest-card-width, 9.75rem) * 1.55);
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  background: transparent;
  padding: 0.7rem;
  cursor: grab;
  text-align: left;
  touch-action: none;
  user-select: none;
  transition:
    border-color 150ms ease,
    background 150ms ease,
    transform 150ms ease;
}

.playtest-stack:hover {
  border-color: var(--playtest-border, rgba(255, 255, 255, 0.1));
  background: color-mix(in srgb, var(--playtest-panel-strong, white) 34%, transparent);
  transform: translateY(-0.08rem);
}

.playtest-stack:active {
  cursor: grabbing;
}

.playtest-stack-empty {
  cursor: default;
}

.playtest-stack-open-only {
  cursor: pointer;
}

.playtest-stack-open-only:active {
  cursor: pointer;
}

.playtest-stack-passive {
  cursor: default;
  pointer-events: none;
}

.playtest-stack-passive:hover {
  border-color: transparent;
  background: transparent;
  transform: none;
}

.playtest-stack-dragging-top {
  opacity: 0.5;
}

.playtest-stack-collapsed {
  display: grid;
  width: var(--playtest-stack-button-width, 3.25rem);
  min-height: calc(var(--playtest-card-width, 9.75rem) * 1.18);
  place-items: center;
  border-color: var(--playtest-border, rgba(255, 255, 255, 0.1));
  border-radius: 999px;
  background: color-mix(in srgb, var(--playtest-panel-strong, white) 42%, transparent);
  padding: 0.55rem 0.3rem;
}

.playtest-stack-title,
.playtest-stack-count {
  position: relative;
  z-index: 5;
  color: var(--playtest-text-muted, rgba(255, 255, 255, 0.84));
  font-size: 0.78rem;
  font-weight: 700;
}

.playtest-stack-header {
  display: flex;
  min-height: 1.25rem;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.playtest-stack-preview {
  position: relative;
  display: grid;
  min-height: calc(var(--playtest-card-width, 9.75rem) * 1.4);
  place-items: center;
  padding-top: 0.45rem;
}

.playtest-stack-collapsed .playtest-stack-header {
  display: contents;
}

.playtest-stack-collapsed .playtest-stack-title {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  letter-spacing: 0;
}

.playtest-stack-collapsed .playtest-stack-count {
  position: absolute;
  top: 0.4rem;
  right: auto;
  left: 50%;
  transform: translateX(-50%);
  border-radius: 999px;
  background: color-mix(in srgb, var(--playtest-surface, black) 44%, transparent);
  padding: 0.05rem 0.35rem;
}

.playtest-stack-collapsed .playtest-stack-preview {
  display: none;
}

.playtest-stack-shadow,
.playtest-stack-card {
  width: var(--playtest-card-width, 9.75rem);
  aspect-ratio: 63 / 88;
  border-radius: 0.45rem;
}

.playtest-stack-shadow {
  position: absolute;
  border: 1px solid var(--playtest-border, rgba(255, 255, 255, 0.08));
  background: color-mix(in srgb, var(--playtest-panel-strong, white) 34%, transparent);
}

.playtest-stack-shadow-one {
  transform: translate(0.22rem, -0.14rem) rotate(2deg);
}

.playtest-stack-shadow-two {
  transform: translate(-0.2rem, 0.18rem) rotate(-2.5deg);
}

.playtest-stack-shuffling .playtest-stack-shadow-one {
  animation: playtest-stack-shuffle-one 650ms ease-in-out;
}

.playtest-stack-shuffling .playtest-stack-shadow-two {
  animation: playtest-stack-shuffle-two 650ms ease-in-out;
}

.playtest-stack-shuffling .playtest-stack-card {
  animation: playtest-stack-shuffle-top 650ms ease-in-out;
}

.playtest-stack-card {
  position: relative;
  z-index: 3;
  display: grid;
  place-items: stretch;
  overflow: hidden;
  border: 0.2rem solid color-mix(in srgb, var(--playtest-border, white) 80%, transparent);
  background: rgba(0, 0, 0, 0.25);
  box-shadow: 0 1rem 1.2rem rgba(0, 0, 0, 0.28);
}

.playtest-stack-card img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.playtest-stack-no-image {
  display: grid;
  place-items: center;
  padding: 0.4rem;
  color: var(--playtest-text-muted, rgba(255, 255, 255, 0.72));
  font-size: 0.65rem;
  font-weight: 700;
  text-align: center;
}

.playtest-stack-card-back {
  display: block;
  width: 100%;
  height: 100%;
  background:
    radial-gradient(circle at 50% 46%, rgba(245, 158, 11, 0.75), transparent 18%),
    radial-gradient(circle at 34% 35%, rgba(59, 130, 246, 0.7), transparent 12%),
    radial-gradient(circle at 65% 60%, rgba(239, 68, 68, 0.62), transparent 14%),
    linear-gradient(145deg, #5c3516, #92622d 46%, #3d2412);
}

.playtest-stack-zoom-overlay {
  position: fixed;
  z-index: 2147483647;
  pointer-events: none;
  filter: drop-shadow(0 2rem 2.2rem rgba(0, 0, 0, 0.54));
}

.playtest-stack-zoom-content {
  width: 100%;
  height: 100%;
}

.playtest-stack-zoom-card {
  display: grid;
  width: 100%;
  height: 100%;
  place-items: stretch;
  overflow: hidden;
  border: 0.32rem solid color-mix(in srgb, var(--playtest-border, white) 82%, transparent);
  border-radius: 0.8rem;
  background: rgba(0, 0, 0, 0.25);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--playtest-panel-strong, white) 18%, transparent);
}

.playtest-stack-zoom-card img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.playtest-stack-zoom-no-image {
  display: grid;
  place-items: center;
  padding: 1rem;
  color: var(--playtest-text-muted, rgba(255, 255, 255, 0.72));
  font-size: 1rem;
  font-weight: 800;
  text-align: center;
}

.playtest-stack-empty-label {
  color: var(--playtest-text-soft, rgba(255, 255, 255, 0.36));
  font-size: 0.85rem;
  font-weight: 700;
}

@keyframes playtest-stack-shuffle-one {
  0%,
  100% {
    transform: translate(0.22rem, -0.14rem) rotate(2deg);
  }
  28% {
    transform: translate(0.72rem, -0.38rem) rotate(9deg);
  }
  62% {
    transform: translate(-0.44rem, 0.22rem) rotate(-7deg);
  }
}

@keyframes playtest-stack-shuffle-two {
  0%,
  100% {
    transform: translate(-0.2rem, 0.18rem) rotate(-2.5deg);
  }
  32% {
    transform: translate(-0.7rem, 0.44rem) rotate(-10deg);
  }
  68% {
    transform: translate(0.48rem, -0.18rem) rotate(6deg);
  }
}

@keyframes playtest-stack-shuffle-top {
  0%,
  100% {
    transform: rotate(0deg);
  }
  35% {
    transform: rotate(-2.4deg);
  }
  70% {
    transform: rotate(2deg);
  }
}

@media (max-width: 767px) {
  .playtest-stack-shadow,
  .playtest-stack-card {
    width: min(var(--playtest-card-width, 9.75rem), 6.7rem);
  }
}
</style>
