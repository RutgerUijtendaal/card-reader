<template>
  <div
    v-if="open"
    class="playtester-stack-popover"
    :style="popoverStyle"
    :data-testid="testId"
  >
    <PlaytestStackBrowser
      :title="title"
      subtitle="Inspect this stack by card identity."
      :instances="instances"
      :card-back-url="cardBackUrl"
      :card-interactive="cardInteractive"
      :dragging-instance-ids="draggingInstanceIds"
      :drop-zone-id="dropZoneId"
      closable
      flush
      search-placeholder="Search stack"
      @close="emit('close')"
      @pointer-card="handleCardPointer"
      @context-card="handleCardContextMenu"
      @hover="emit('hover', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import PlaytestStackBrowser from '@/modules/playtester/components/PlaytestStackBrowser.vue';
import type {
  PlaytestCardInstance,
  PlaytestCardSource,
  PlaytestHoverTarget,
  PlaytestZoneId,
} from '@/modules/playtester/types';

const props = withDefaults(defineProps<{
  open: boolean;
  title: string;
  instances: PlaytestCardInstance[];
  cardBackUrl: string | null;
  cardInteractive?: boolean;
  draggingInstanceIds?: string[];
  dropZoneId?: PlaytestZoneId | null;
  bottomOffsetPx?: number | null;
  testId?: string;
}>(), {
  bottomOffsetPx: null,
  cardInteractive: true,
  draggingInstanceIds: () => [],
  dropZoneId: null,
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
  style['--playtester-stack-popover-bottom'] = `calc(${props.bottomOffsetPx}px + var(--playtester-stack-popover-gap))`;
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
  --playtester-stack-popover-gap: 2rem;
  --playtester-stack-popover-bottom: calc(clamp(13rem, 22vh, 18rem) + var(--playtester-stack-popover-gap));
  position: absolute;
  top: 1rem;
  right: 1rem;
  bottom: var(--playtester-stack-popover-bottom);
  z-index: 40;
  width: min(27rem, calc(100% - 2rem));
}

.playtester-stack-popover :deep(.playtest-stack-browser) {
  height: 100%;
  max-height: 100%;
}
</style>
