<template>
  <div
    v-if="open"
    class="playtester-stack-popover"
    :style="popoverStyle"
    :data-testid="testId"
  >
    <section class="playtester-stack-panel">
      <header class="playtester-stack-panel-header">
        <div>
          <h3>{{ title }}</h3>
          <p>{{ instances.length }} cards</p>
        </div>
        <button
          class="btn-secondary"
          type="button"
          @click="emit('close')"
        >
          Close
        </button>
      </header>
      <div class="playtester-stack-card-grid app-scrollbar">
        <PlaytestCard
          v-for="instance in instances"
          :key="instance.instanceId"
          :instance="instance"
          :activatable="false"
          :dragging="draggingInstanceIds.includes(instance.instanceId)"
          :card-back-url="cardBackUrl"
          :interactive="cardInteractive"
          @pointer-card="handleCardPointer"
          @context-menu="handleCardContextMenu"
          @hover="emit('hover', $event)"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import PlaytestCard from '@/modules/playtester/components/PlaytestCard.vue';
import type {
  PlaytestCardInstance,
  PlaytestCardSource,
  PlaytestHoverTarget,
} from '@/modules/playtester/types';

const props = withDefaults(defineProps<{
  open: boolean;
  title: string;
  instances: PlaytestCardInstance[];
  cardBackUrl: string | null;
  cardInteractive?: boolean;
  draggingInstanceIds?: string[];
  bottomOffsetPx?: number | null;
  testId?: string;
}>(), {
  bottomOffsetPx: null,
  cardInteractive: true,
  draggingInstanceIds: () => [],
  testId: 'playtest-stack-overlay',
});

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'pointer-card', instanceId: string, source: PlaytestCardSource, event: PointerEvent): void;
  (e: 'context-card', instanceId: string, event: MouseEvent): void;
  (e: 'hover', target: PlaytestHoverTarget | null): void;
}>();

const popoverStyle = computed<Record<string, string>>(() => {
  const style: Record<string, string> = {};
  if (props.bottomOffsetPx === null || props.bottomOffsetPx <= 0) {
    return style;
  }
  style['--playtester-stack-popover-bottom'] = `${props.bottomOffsetPx}px`;
  return style;
});

const handleCardPointer = (
  instanceId: string,
  source: PlaytestCardSource,
  event: PointerEvent,
): void => {
  emit('pointer-card', instanceId, source, event);
};

const handleCardContextMenu = (instanceId: string, event: MouseEvent): void => {
  emit('context-card', instanceId, event);
};
</script>

<style scoped>
.playtester-stack-popover {
  --playtester-stack-popover-bottom: clamp(13rem, 22vh, 18rem);
  position: absolute;
  right: 1rem;
  bottom: var(--playtester-stack-popover-bottom);
  z-index: 40;
  width: min(48rem, calc(100% - 2rem));
}

.playtester-stack-panel {
  max-height: min(36rem, calc(100vh - var(--playtester-stack-popover-bottom) - 2rem));
  overflow: hidden;
  border: 1px solid var(--playtest-border);
  border-radius: 0.9rem;
  background: var(--playtest-panel-strong);
  box-shadow: 0 2rem 5rem rgba(15, 23, 42, 0.22);
}

.playtester-stack-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
  border-bottom: 1px solid var(--playtest-border);
}

.playtester-stack-panel-header h3 {
  color: var(--playtest-text);
  font-size: 1rem;
  font-weight: 800;
}

.playtester-stack-panel-header p {
  color: var(--playtest-text-soft);
  font-size: 0.82rem;
  font-weight: 700;
}

.playtester-stack-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(var(--playtest-card-width, 9.75rem), 1fr));
  max-height: min(28rem, calc(100vh - var(--playtester-stack-popover-bottom) - 9rem));
  gap: 1rem;
  overflow: auto;
  padding: 1rem;
}
</style>
