<template>
  <div
    class="playtest-stack"
    :class="[
      instances.length === 0 ? 'playtest-stack-empty' : '',
      collapsed ? 'playtest-stack-collapsed' : '',
      draggingTop ? 'playtest-stack-dragging-top' : '',
    ]"
    :data-testid="`playtest-${zoneId}-zone`"
    :data-playtest-stack-zone-id="zoneId"
    role="button"
    tabindex="0"
    @click="runDefaultAction"
    @keydown.enter.prevent="runDefaultAction"
    @keydown.space.prevent="runDefaultAction"
    @pointerdown="handlePointerDown"
    @contextmenu.prevent="emit('context-menu', zoneId, $event)"
    @mouseenter="emit('hover', { type: 'stack', zoneId })"
    @mouseleave="emit('hover', null)"
  >
    <div class="playtest-stack-header">
      <span class="playtest-stack-title">{{ label }}</span>
      <span class="playtest-stack-count">{{ instances.length }}</span>
    </div>

    <div class="playtest-stack-preview">
      <template v-if="instances.length > 0">
        <div class="playtest-stack-shadow playtest-stack-shadow-one" />
        <div class="playtest-stack-shadow playtest-stack-shadow-two" />
        <div class="playtest-stack-card">
          <img
            v-if="face === 'front' && topInstance?.card.image_url"
            :src="toAbsoluteApiUrl(topInstance.card.image_url)"
            :alt="topInstance.card.name"
            draggable="false"
          >
          <div
            v-else-if="face === 'front'"
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
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';
import type {
  PlaytestCardInstance,
  PlaytestHoverTarget,
  PlaytestStackDefaultAction,
  PlaytestStackFace,
  PlaytestZoneId,
} from '@/modules/playtester/types';

const props = defineProps<{
  zoneId: PlaytestZoneId;
  label: string;
  instances: PlaytestCardInstance[];
  face: PlaytestStackFace;
  cardBackUrl: string | null;
  collapsed: boolean;
  defaultAction: PlaytestStackDefaultAction;
  draggingTop: boolean;
}>();

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

const runDefaultAction = (): void => {
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
  if (event.button !== 0) {
    return;
  }
  const instance = topInstance.value;
  if (!instance) {
    return;
  }
  emit('pointer-top', props.zoneId, instance.instanceId, event);
};
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

.playtest-stack-empty-label {
  color: var(--playtest-text-soft, rgba(255, 255, 255, 0.36));
  font-size: 0.85rem;
  font-weight: 700;
}

@media (max-width: 767px) {
  .playtest-stack-shadow,
  .playtest-stack-card {
    width: min(var(--playtest-card-width, 9.75rem), 6.7rem);
  }
}
</style>
