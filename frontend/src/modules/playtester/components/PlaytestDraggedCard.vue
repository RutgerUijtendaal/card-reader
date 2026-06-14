<template>
  <Teleport to="body">
    <div
      class="playtest-dragged-card"
      data-testid="playtest-dragged-card"
      :style="dragStyle"
    >
      <PlaytestCard
        :instance="instance"
        @activate="noop"
        @pointer-card="noopPointer"
        @context-menu="noopContext"
        @hover="noopHover"
      />
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import PlaytestCard from '@/modules/playtester/components/PlaytestCard.vue';
import type {
  PlaytestCardInstance,
  PlaytestDraggedCard,
} from '@/modules/playtester/types';

const props = defineProps<{
  drag: PlaytestDraggedCard;
  instance: PlaytestCardInstance;
}>();

const dragStyle = computed(() => ({
  left: `${props.drag.pointerX - props.drag.pointerOffsetX}px`,
  top: `${props.drag.pointerY - props.drag.pointerOffsetY}px`,
}));

const noop = (): void => undefined;
const noopPointer = (): void => undefined;
const noopContext = (): void => undefined;
const noopHover = (): void => undefined;
</script>

<style scoped>
.playtest-dragged-card {
  position: fixed;
  z-index: 10000;
  pointer-events: none;
  transform: rotate(1.5deg) scale(1.02);
  filter: drop-shadow(0 1.4rem 1.6rem rgba(0, 0, 0, 0.46));
}
</style>
