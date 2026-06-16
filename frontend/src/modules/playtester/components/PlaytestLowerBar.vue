<template>
  <div
    ref="lowerBarRef"
    class="playtester-lower"
  >
    <section
      class="playtester-hand"
      data-testid="playtest-hand-zone"
      data-playtest-drop-zone="hand"
    >
      <div class="playtester-hand-bar">
        <span>{{ handTitle }}</span>
        <span class="theme-section-muted">{{ handSubtitle }}</span>
      </div>
      <div class="playtester-hand-fan">
        <div
          v-for="(instance, index) in handInstances"
          :key="instance.instanceId"
          class="playtester-hand-card"
          :style="handCardStyle(index, handInstances.length)"
        >
          <PlaytestCard
            :instance="instance"
            :dragging="draggingInstanceIds.includes(instance.instanceId)"
            :card-back-url="cardBackUrl"
            :interactive="cardInteractive"
            @activate="emit('activate-card', $event)"
            @pointer-card="handleCardPointer"
            @context-menu="handleCardContextMenu"
            @hover="emit('hover', $event)"
          />
        </div>

        <template v-if="handInstances.length === 0">
          <span
            v-for="index in placeholderHandSize"
            :key="`hand-placeholder-${index}`"
            class="playtester-hand-placeholder-card"
            :class="cardBackUrl ? 'playtester-hand-placeholder-card-image' : ''"
            :style="handCardStyle(index - 1, placeholderHandSize)"
          >
            <img
              v-if="cardBackUrl"
              :src="cardBackUrl"
              alt=""
              draggable="false"
            >
          </span>
        </template>
      </div>
    </section>

    <div class="playtester-piles">
      <PlaytestStack
        v-for="zone in stackZones"
        :key="zone.id"
        :zone-id="zone.id"
        :label="zone.label"
        :instances="zone.instances"
        :face="zone.face"
        :card-back-url="cardBackUrl"
        :collapsed="zone.collapsed"
        :default-action="zone.defaultAction"
        :dragging-top="draggingTopInstanceId === stackTopInstanceId(zone)"
        :shuffling="shufflingStackZone === zone.id"
        :interactive="stackInteractive"
        :draggable="stackDraggable"
        @open="emit('open-stack', $event)"
        @draw="emit('draw-stack', $event)"
        @pointer-top="handleStackPointer"
        @context-menu="handleStackContextMenu"
        @hover="emit('hover', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useResizeObserver } from '@vueuse/core';
import { ref } from 'vue';
import PlaytestCard from '@/modules/playtester/components/PlaytestCard.vue';
import PlaytestStack from '@/modules/playtester/components/PlaytestStack.vue';
import type {
  PlaytestCardInstance,
  PlaytestCardSource,
  PlaytestHoverTarget,
  PlaytestStackDefinition,
  PlaytestStackFace,
  PlaytestZoneId,
} from '@/modules/playtester/types';

export type PlaytestLowerBarStackZone = PlaytestStackDefinition & {
  instances: PlaytestCardInstance[];
  face: PlaytestStackFace;
  collapsed: boolean;
};

withDefaults(defineProps<{
  handInstances: PlaytestCardInstance[];
  stackZones: PlaytestLowerBarStackZone[];
  cardBackUrl: string | null;
  handTitle?: string;
  handSubtitle?: string;
  placeholderHandSize?: number;
  cardInteractive?: boolean;
  stackInteractive?: boolean;
  stackDraggable?: boolean;
  draggingInstanceIds?: string[];
  draggingTopInstanceId?: string | null;
  shufflingStackZone?: PlaytestZoneId | null;
}>(), {
  cardInteractive: true,
  draggingInstanceIds: () => [],
  draggingTopInstanceId: null,
  handSubtitle: 'Click a card to put it on the board.',
  handTitle: 'Cards in hand',
  placeholderHandSize: 0,
  shufflingStackZone: null,
  stackDraggable: true,
  stackInteractive: true,
});

const emit = defineEmits<{
  (e: 'activate-card', instanceId: string): void;
  (e: 'pointer-card', instanceId: string, source: PlaytestCardSource, event: PointerEvent): void;
  (e: 'context-card', instanceId: string, event: MouseEvent): void;
  (e: 'open-stack', zoneId: PlaytestZoneId): void;
  (e: 'draw-stack', zoneId: PlaytestZoneId): void;
  (e: 'pointer-stack', zoneId: PlaytestZoneId, instanceId: string, event: PointerEvent): void;
  (e: 'context-stack', zoneId: PlaytestZoneId, event: MouseEvent): void;
  (e: 'hover', target: PlaytestHoverTarget | null): void;
  (e: 'resize', width: number, height: number): void;
}>();

const lowerBarRef = ref<HTMLElement | null>(null);

const stackTopInstanceId = (zone: PlaytestLowerBarStackZone): string | null => {
  const instance = zone.id === 'library'
    ? zone.instances[0]
    : zone.instances[zone.instances.length - 1];
  return instance?.instanceId ?? null;
};

const handleCardPointer = (
  instanceId: string,
  source: PlaytestCardSource,
  event: PointerEvent,
): void => {
  if (source.type !== 'card') {
    return;
  }
  emit('pointer-card', instanceId, source, event);
};

const handleCardContextMenu = (instanceId: string, event: MouseEvent): void => {
  emit('context-card', instanceId, event);
};

const handleStackPointer = (zoneId: PlaytestZoneId, instanceId: string, event: PointerEvent): void => {
  emit('pointer-stack', zoneId, instanceId, event);
};

const handleStackContextMenu = (zoneId: PlaytestZoneId, event: MouseEvent): void => {
  emit('context-stack', zoneId, event);
};

const handCardStyle = (index: number, total: number): Record<string, string | number> => {
  const center = index - (total - 1) / 2;
  return {
    marginLeft: index === 0 ? '0' : 'calc(var(--playtest-card-width) * -0.42)',
    transform: `translateY(${Math.abs(center) * 0.42}rem) rotate(${center * 4.2}deg)`,
    zIndex: 30 + index,
  };
};

useResizeObserver(lowerBarRef, ([entry]) => {
  emit('resize', entry?.contentRect.width ?? 0, entry?.contentRect.height ?? 0);
});
</script>

<style scoped>
.playtester-lower {
  position: relative;
  z-index: 30;
  display: flex;
  align-items: stretch;
  flex: 0 0 auto;
  gap: 0.75rem;
  overflow: hidden;
  padding: 0.75rem;
  border-top: 1px solid var(--playtest-border);
  background: var(--playtest-panel-muted);
  backdrop-filter: blur(12px);
}

.playtester-hand {
  flex: 1 1 34rem;
  min-width: 0;
  min-height: calc((var(--playtest-card-width, 9.75rem) * 1.42) + 4rem);
  overflow: hidden;
  border-right: 1px solid var(--playtest-border);
}

.playtester-hand-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.6rem 0.8rem 0;
  color: var(--playtest-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
  user-select: none;
}

.playtester-hand-fan {
  display: flex;
  box-sizing: border-box;
  height: calc((var(--playtest-card-width, 9.75rem) * 1.42) + 2rem);
  min-width: max-content;
  align-items: flex-end;
  justify-content: center;
  padding: 1.25rem 1.5rem 0.75rem;
}

.playtester-hand-card {
  flex: 0 0 auto;
  transition:
    transform 180ms ease,
    margin 180ms ease;
}

.playtester-hand-placeholder-card {
  display: grid;
  width: var(--playtest-card-width);
  aspect-ratio: 63 / 88;
  place-items: stretch;
  overflow: hidden;
  flex: 0 0 auto;
  border: 1px solid var(--playtest-border);
  border-radius: 0.45rem;
  background:
    linear-gradient(145deg, color-mix(in srgb, var(--playtest-panel-strong) 62%, transparent), color-mix(in srgb, var(--playtest-panel-muted) 82%, transparent));
  opacity: 0.55;
}

.playtester-hand-placeholder-card-image {
  background: color-mix(in srgb, var(--playtest-panel-strong) 42%, transparent);
  opacity: 0.68;
}

.playtester-hand-placeholder-card img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.playtester-piles {
  display: flex;
  flex: 0 0 auto;
  align-items: stretch;
  gap: 0.75rem;
}

@media (max-width: 900px) {
  .playtester-lower {
    overflow-x: auto;
  }

  .playtester-hand {
    min-width: 23rem;
  }
}
</style>
