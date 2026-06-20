<template>
  <div class="playtester-topbar">
    <div class="flex flex-wrap items-center gap-2">
      <div class="playtester-history-controls">
        <button
          class="playtester-history-button"
          type="button"
          aria-label="Undo"
          title="Undo (Ctrl+Z)"
          data-testid="playtest-undo"
          :disabled="undoDisabled"
          @click="emit('undo')"
          @pointerup="emit('release-pointer-focus', $event)"
          @pointercancel="emit('release-pointer-focus', $event)"
        >
          <Undo2 class="h-4 w-4" />
        </button>
        <button
          class="playtester-history-button"
          type="button"
          aria-label="Redo"
          title="Redo (Ctrl+Shift+Z or Ctrl+Y)"
          data-testid="playtest-redo"
          :disabled="redoDisabled"
          @click="emit('redo')"
          @pointerup="emit('release-pointer-focus', $event)"
          @pointercancel="emit('release-pointer-focus', $event)"
        >
          <Redo2 class="h-4 w-4" />
        </button>
      </div>
      <span
        class="playtester-topbar-divider"
        aria-hidden="true"
      />
      <label class="playtester-scale-control theme-section-muted">
        Scale
        <input
          class="playtester-scale"
          type="range"
          :value="cardScale"
          min="0.5"
          max="1.6"
          step="0.05"
          @input="emit('update-card-scale', $event)"
          @pointerup="emit('release-pointer-focus', $event)"
          @pointercancel="emit('release-pointer-focus', $event)"
        >
      </label>
    </div>

    <div class="flex flex-wrap items-center justify-end gap-2">
      <button
        class="btn-primary"
        type="button"
        @click="emit('next-turn')"
        @pointerup="emit('release-pointer-focus', $event)"
        @pointercancel="emit('release-pointer-focus', $event)"
      >
        Next turn
      </button>
      <button
        class="btn-secondary"
        type="button"
        :disabled="!canResetSetup"
        @click="emit('reset-setup')"
        @pointerup="emit('release-pointer-focus', $event)"
        @pointercancel="emit('release-pointer-focus', $event)"
      >
        Reset to Setup
      </button>
      <button
        class="btn-danger-secondary"
        type="button"
        @click="emit('restart')"
        @pointerup="emit('release-pointer-focus', $event)"
        @pointercancel="emit('release-pointer-focus', $event)"
      >
        Restart
      </button>
    </div>
  </div>

  <div
    ref="boardRef"
    class="playtester-board"
    data-testid="playtest-board-zone"
    data-playtest-drop-zone="board"
    @pointerdown="emit('start-board-selection', $event)"
    @pointermove="emit('remember-board-pointer', $event)"
    @wheel="emit('remember-board-pointer', $event)"
  >
    <div class="playtester-board-label">
      <span>Board</span>
      <span>{{ playInstances.length }} cards</span>
    </div>

    <div
      v-if="playInstances.length === 0"
      class="playtester-board-empty"
    >
      Drag cards here or click a card in hand.
    </div>

    <div
      v-for="pile in visualPiles"
      :key="pile.groupId"
      class="playtester-board-pile"
    >
      <PlaytestVisualPile
        :group-id="pile.groupId"
        :instances="pile.instances"
        :dragged-instance-ids="activeDraggedInstanceIds"
        :selected-instance-ids="selectedBoardInstanceIds"
        :card-back-url="currentCardBackUrl"
        @activate="emit('activate-card', $event)"
        @pointer-card="(instanceId, source, event) => emit('pointer-card', instanceId, source, event)"
        @context-menu="(instanceId, event) => emit('context-card', instanceId, event)"
        @hover="emit('hover', $event)"
      />
    </div>

    <div
      v-for="(instance, index) in loosePlayInstances"
      :key="instance.instanceId"
      class="playtester-board-card"
      data-testid="playtest-board-card"
      :style="boardCardStyle(instance, index)"
    >
      <PlaytestCard
        :instance="instance"
        :dragging="activeDraggedInstanceIds.includes(instance.instanceId)"
        :selected="selectedBoardInstanceIds.includes(instance.instanceId)"
        :card-back-url="currentCardBackUrl"
        @activate="emit('activate-card', $event)"
        @pointer-card="(instanceId, source, event) => emit('pointer-card', instanceId, source, event)"
        @context-menu="(instanceId, event) => emit('context-card', instanceId, event)"
        @hover="emit('hover', $event)"
      />
    </div>

    <div
      v-if="boardSelectionActive"
      class="playtester-selection-box"
      data-testid="playtest-selection-box"
      :style="selectionBoxStyle"
    />
  </div>

  <PlaytestLowerBar
    :hand-instances="handInstances"
    :hand-title="`Cards in hand: ${handInstances.length}`"
    :stack-zones="stackZones"
    :card-back-url="currentCardBackUrl"
    :dragging-instance-ids="activeDraggedInstanceIds"
    :dragging-top-instance-id="activeDragInstanceId"
    :shuffling-stack-zone="shufflingStackZone"
    @activate-card="emit('activate-card', $event)"
    @pointer-card="(instanceId, source, event) => emit('pointer-card', instanceId, source, event)"
    @context-card="(instanceId, event) => emit('context-card', instanceId, event)"
    @open-stack="emit('open-stack', $event)"
    @draw-stack="emit('draw-stack', $event)"
    @pointer-stack="(zoneId, instanceId, event) => emit('pointer-stack', zoneId, instanceId, event)"
    @context-stack="(zoneId, event) => emit('context-stack', zoneId, event)"
    @hover="emit('hover', $event)"
    @resize="(width, height) => emit('resize', width, height)"
  />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { Redo2, Undo2 } from 'lucide-vue-next';
import PlaytestCard from '@/modules/playtester/components/PlaytestCard.vue';
import PlaytestLowerBar, { type PlaytestLowerBarStackZone } from '@/modules/playtester/components/PlaytestLowerBar.vue';
import PlaytestVisualPile from '@/modules/playtester/components/PlaytestVisualPile.vue';
import type {
  PlaytestCardInstance,
  PlaytestCardSource,
  PlaytestHoverTarget,
  PlaytestZoneId,
} from '@/modules/playtester/types';

export type PlaytestActiveVisualPile = {
  groupId: string;
  instances: PlaytestCardInstance[];
};

defineProps<{
  activeDragInstanceId: string | null;
  activeDraggedInstanceIds: string[];
  boardSelectionActive: boolean;
  canResetSetup: boolean;
  cardScale: number;
  currentCardBackUrl: string | null;
  handInstances: PlaytestCardInstance[];
  loosePlayInstances: PlaytestCardInstance[];
  playInstances: PlaytestCardInstance[];
  redoDisabled: boolean;
  selectedBoardInstanceIds: string[];
  selectionBoxStyle: Record<string, string | undefined>;
  shufflingStackZone: PlaytestZoneId | null;
  stackZones: PlaytestLowerBarStackZone[];
  undoDisabled: boolean;
  visualPiles: PlaytestActiveVisualPile[];
}>();

const emit = defineEmits<{
  (e: 'activate-card', instanceId: string): void;
  (e: 'board-ref', element: HTMLElement | null): void;
  (e: 'context-card', instanceId: string, event: MouseEvent): void;
  (e: 'context-stack', zoneId: PlaytestZoneId, event: MouseEvent): void;
  (e: 'draw-stack', zoneId: PlaytestZoneId): void;
  (e: 'hover', target: PlaytestHoverTarget | null): void;
  (e: 'next-turn'): void;
  (e: 'open-stack', zoneId: PlaytestZoneId): void;
  (e: 'pointer-card', instanceId: string, source: PlaytestCardSource, event: PointerEvent): void;
  (e: 'pointer-stack', zoneId: PlaytestZoneId, instanceId: string, event: PointerEvent): void;
  (e: 'redo'): void;
  (e: 'release-pointer-focus', event: PointerEvent): void;
  (e: 'remember-board-pointer', event: PointerEvent | WheelEvent): void;
  (e: 'reset-setup'): void;
  (e: 'resize', width: number, height: number): void;
  (e: 'restart'): void;
  (e: 'start-board-selection', event: PointerEvent): void;
  (e: 'undo'): void;
  (e: 'update-card-scale', event: Event): void;
}>();

const boardRef = ref<HTMLElement | null>(null);

const boardCardStyle = (instance: PlaytestCardInstance, index: number): Record<string, string | number> => {
  const x = instance.boardX ?? 16 + (index % 5) * 16;
  const y = instance.boardY ?? 22 + Math.floor(index / 5) * 24;
  return {
    left: `${x}%`,
    top: `${y}%`,
    zIndex: 20 + index,
  };
};

watch(boardRef, (element) => {
  emit('board-ref', element);
});

onMounted(() => {
  emit('board-ref', boardRef.value);
});

onBeforeUnmount(() => {
  emit('board-ref', null);
});
</script>

<style scoped>
.playtester-topbar {
  position: relative;
  z-index: 30;
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem;
  border-bottom: 1px solid color-mix(in srgb, var(--playtest-border) 82%, transparent);
  background:
    linear-gradient(
      color-mix(in srgb, var(--playtest-surface) 38%, transparent),
      color-mix(in srgb, var(--playtest-surface) 38%, transparent)
    ),
    linear-gradient(var(--playtest-grid-line) 1px, transparent 1px),
    linear-gradient(90deg, var(--playtest-grid-line) 1px, transparent 1px),
    transparent;
  background-size: auto, 1.35rem 1.35rem, 1.35rem 1.35rem, auto;
  box-shadow: 0 0.75rem 1.5rem color-mix(in srgb, var(--color-shadow) 16%, transparent);
  backdrop-filter: blur(12px);
}

.playtester-scale-control {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding-right: 0.35rem;
  font-size: 0.78rem;
  font-weight: 700;
}

.playtester-topbar-divider {
  width: 1px;
  height: 1.55rem;
  background: var(--playtest-border);
}

.playtester-history-controls {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.playtester-history-button {
  display: inline-flex;
  width: 2rem;
  height: 2rem;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--playtest-border);
  border-radius: 0.45rem;
  background: color-mix(in srgb, var(--playtest-panel-strong) 74%, transparent);
  color: var(--playtest-text-muted);
  transition:
    background-color 120ms ease,
    border-color 120ms ease,
    color 120ms ease,
    opacity 120ms ease;
}

.playtester-history-button:not(:disabled):hover,
.playtester-history-button:not(:disabled):focus-visible {
  border-color: color-mix(in srgb, var(--color-accent) 58%, var(--playtest-border));
  background: color-mix(in srgb, var(--color-accent) 18%, var(--playtest-panel-strong));
  color: var(--playtest-text);
}

.playtester-history-button:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

.playtester-board {
  position: relative;
  min-height: 20rem;
  flex: 1 1 auto;
}

.playtester-board-label {
  position: absolute;
  top: 0.85rem;
  left: 1rem;
  z-index: 10;
  display: flex;
  gap: 0.7rem;
  color: var(--playtest-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
  user-select: none;
}

.playtester-board-empty {
  position: absolute;
  inset: 45% auto auto 50%;
  z-index: 1;
  transform: translate(-50%, -50%);
  color: var(--playtest-text-soft);
  font-size: 0.95rem;
  font-weight: 700;
  pointer-events: none;
  user-select: none;
}

.playtester-board-card {
  position: absolute;
  transform: translate(-50%, -50%);
  animation: playtester-board-card-in 120ms ease-out;
}

.playtester-board-pile {
  animation: playtester-board-card-in 120ms ease-out;
}

.playtester-selection-box {
  position: absolute;
  z-index: 35;
  border: 2px solid color-mix(in srgb, var(--color-accent) 76%, white 24%);
  background: color-mix(in srgb, var(--color-accent) 28%, transparent);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.34),
    inset 0 0 0 1px rgba(0, 0, 0, 0.22),
    0 0.5rem 1.5rem rgba(0, 0, 0, 0.22);
  pointer-events: none;
}

.playtester-scale {
  width: 8rem;
  accent-color: var(--color-accent);
}

@media (max-width: 767px) {
  .playtester-topbar {
    align-items: stretch;
    flex-direction: column;
  }

  .playtester-board {
    min-height: 22rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .playtester-topbar *,
  .playtester-board * {
    animation-duration: 1ms !important;
    transition-duration: 1ms !important;
  }
}

@keyframes playtester-board-card-in {
  from {
    opacity: 0;
    filter: blur(0.08rem);
  }

  to {
    opacity: 1;
    filter: blur(0);
  }
}
</style>
