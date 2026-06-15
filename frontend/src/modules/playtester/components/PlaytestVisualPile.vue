<template>
  <div
    class="playtest-visual-pile"
    data-testid="playtest-visual-pile"
    :data-playtest-pile-group-id="groupId"
    :style="pileStyle"
  >
    <div
      v-for="(instance, index) in instances"
      :key="instance.instanceId"
      class="playtest-visual-pile-card"
      :style="cardStyle(index)"
    >
      <PlaytestCard
        :instance="instance"
        pile-member
        :dragging="draggedInstanceIds.includes(instance.instanceId)"
        :selected="selectedInstanceIds.includes(instance.instanceId)"
        :card-back-url="cardBackUrl"
        @activate="emit('activate', $event)"
        @pointer-card="handlePointerCard"
        @context-menu="handleContextMenu"
        @hover="emit('hover', $event)"
      />
    </div>
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

const props = defineProps<{
  groupId: string;
  instances: PlaytestCardInstance[];
  draggedInstanceIds: string[];
  selectedInstanceIds: string[];
  cardBackUrl: string | null;
}>();

const emit = defineEmits<{
  (e: 'activate', instanceId: string): void;
  (e: 'pointer-card', instanceId: string, source: PlaytestCardSource, event: PointerEvent): void;
  (e: 'context-menu', instanceId: string, event: MouseEvent): void;
  (e: 'hover', target: PlaytestHoverTarget | null): void;
}>();

const anchor = computed(() => props.instances[0]);
const pileStyle = computed(() => ({
  left: `${anchor.value?.boardX ?? 16}%`,
  top: `${anchor.value?.boardY ?? 22}%`,
}));

const cardStyle = (index: number): Record<string, string | number> => ({
  top: `calc(${index} * var(--playtest-card-width, 9.75rem) * 0.14)`,
  zIndex: 20 + index,
});

const handlePointerCard = (instanceId: string, source: PlaytestCardSource, event: PointerEvent): void => {
  emit('pointer-card', instanceId, source, event);
};

const handleContextMenu = (instanceId: string, event: MouseEvent): void => {
  emit('context-menu', instanceId, event);
};
</script>

<style scoped>
.playtest-visual-pile {
  position: absolute;
  width: var(--playtest-card-width, 9.75rem);
  height: calc(var(--playtest-card-width, 9.75rem) * 88 / 63);
  transform: translate(-50%, -50%);
}

.playtest-visual-pile-card {
  position: absolute;
  left: 0;
  width: var(--playtest-card-width, 9.75rem);
}

</style>
