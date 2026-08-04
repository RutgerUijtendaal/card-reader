<template>
  <section
    class="playtest-opening-hand-stage"
    data-testid="playtest-opening-hand"
  >
    <h3>Opening hand</h3>
    <div class="playtest-opening-hand">
      <div
        v-for="(instance, index) in handInstances"
        :key="instance.instanceId"
        class="playtest-opening-hand-card"
        :style="openingHandCardStyle(index, handInstances.length)"
      >
        <PlaytestCard
          :instance="instance"
          :interactive="false"
        />
      </div>
      <div
        v-if="handInstances.length === 0"
        class="playtest-opening-empty"
      >
        No cards available.
      </div>
    </div>
    <div class="playtest-opening-hand-actions">
      <label class="playtest-opening-hand-size">
        Hand
        <input
          class="input-base h-9 w-20 px-3 py-1"
          type="number"
          min="0"
          max="99"
          :value="handSize"
          @input="emitHandSize"
        >
      </label>
      <button
        class="btn-primary"
        type="button"
        @click="emit('keep')"
      >
        Keep this
      </button>
      <button
        class="btn-secondary"
        type="button"
        @click="emit('mulligan')"
      >
        Mulligan [{{ mulliganCount }}]
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import PlaytestCard from '@/features/playtester/components/PlaytestCard.vue';
import type { PlaytestCardInstance } from '@/features/playtester/types';

defineProps<{ handInstances: PlaytestCardInstance[]; handSize: number; mulliganCount: number }>();
const emit = defineEmits<{
  (e: 'keep'): void;
  (e: 'mulligan'): void;
  (e: 'update-hand-size', handSize: number): void;
}>();
const emitHandSize = (event: Event): void => {
  const value = (event.target as HTMLInputElement).value;
  if (value.trim() === '') return;
  const handSize = Number(value);
  if (Number.isFinite(handSize)) emit('update-hand-size', handSize);
};
const openingHandCardStyle = (index: number, total: number): Record<string, string | number> => {
  const center = index - (total - 1) / 2;
  return {
    marginLeft: index === 0 ? '0' : 'calc(var(--playtest-card-width) * -0.34)',
    transform: `translateY(${center * center * 0.3}rem) rotate(${center * 5.2}deg)`,
    transformOrigin: '50% 112%',
    zIndex: 30 + index,
  };
};
</script>
