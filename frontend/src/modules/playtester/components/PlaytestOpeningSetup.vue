<template>
  <section
    class="playtest-opening"
    data-testid="playtest-opening-setup"
  >
    <div class="playtest-opening-actions">
      <p class="playtest-opening-eyebrow">
        Opening hand
      </p>
      <div class="playtest-opening-controls">
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
          Mulligan
        </button>
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
      </div>
    </div>

    <div
      class="playtest-opening-hand"
      data-testid="playtest-opening-hand"
    >
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

    <div
      ref="bottomRef"
      class="playtest-opening-bottom"
    >
      <div
        class="playtest-opening-selections"
        :class="setupInstances.length === 0 ? 'playtest-opening-selections-single' : ''"
      >
        <section
          class="playtest-opening-selection-panel"
          data-testid="playtest-opening-mana"
        >
          <div class="playtest-opening-section-heading">
            <div>
              <h3>Starting Mana</h3>
              <p>Select exact copies that should begin in play.</p>
            </div>
            <span>{{ selectedManaIds.length }} selected</span>
          </div>
          <div
            class="playtest-opening-card-grid app-scrollbar"
            @wheel="scrollSelectionWheel"
          >
            <button
              v-for="instance in manaInstances"
              :key="instance.instanceId"
              class="playtest-opening-card-choice"
              :class="selectedManaSet.has(instance.instanceId) ? 'playtest-opening-card-choice-selected' : ''"
              type="button"
              :aria-pressed="selectedManaSet.has(instance.instanceId)"
              @click="emit('toggle-mana', instance.instanceId, !selectedManaSet.has(instance.instanceId))"
            >
              <PlaytestCard
                :instance="instance"
                compact
                :interactive="false"
                :selected="selectedManaSet.has(instance.instanceId)"
              />
            </button>
            <p
              v-if="manaInstances.length === 0"
              class="playtest-opening-empty"
            >
              No mana cards in this mainboard.
            </p>
          </div>
        </section>

        <section
          v-if="setupInstances.length > 0"
          class="playtest-opening-selection-panel"
          data-testid="playtest-opening-setup-cards"
        >
          <div class="playtest-opening-section-heading">
            <div>
              <h3>Setup Cards</h3>
              <p>Cards with Setup effects to check before keeping.</p>
            </div>
            <span>{{ setupInstances.length }} found</span>
          </div>
          <div
            class="playtest-opening-card-grid app-scrollbar"
            @wheel="scrollSelectionWheel"
          >
            <div
              v-for="instance in setupInstances"
              :key="instance.instanceId"
              class="playtest-opening-card-choice playtest-opening-card-hint"
            >
              <PlaytestCard
                :instance="instance"
                compact
                :interactive="false"
              />
            </div>
          </div>
        </section>
      </div>

      <div
        v-if="$slots.stacks"
        class="playtest-opening-stacks"
      >
        <slot name="stacks" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useResizeObserver } from '@vueuse/core';
import PlaytestCard from '@/modules/playtester/components/PlaytestCard.vue';
import type { PlaytestCardInstance } from '@/modules/playtester/types';

const props = defineProps<{
  handInstances: PlaytestCardInstance[];
  manaInstances: PlaytestCardInstance[];
  setupInstances: PlaytestCardInstance[];
  selectedManaIds: string[];
  handSize: number;
}>();

const emit = defineEmits<{
  (e: 'keep'): void;
  (e: 'mulligan'): void;
  (e: 'update-hand-size', handSize: number): void;
  (e: 'toggle-mana', instanceId: string, selected: boolean): void;
  (e: 'bottom-resize', width: number): void;
}>();

const bottomRef = ref<HTMLElement | null>(null);
const selectedManaSet = computed(() => new Set(props.selectedManaIds));

useResizeObserver(bottomRef, ([entry]) => {
  emit('bottom-resize', entry?.contentRect.width ?? 0);
});

const emitHandSize = (event: Event): void => {
  const value = (event.target as HTMLInputElement).value;
  if (value.trim() === '') {
    return;
  }
  const handSize = Number(value);
  if (!Number.isFinite(handSize)) {
    return;
  }
  emit('update-hand-size', handSize);
};

const scrollSelectionWheel = (event: WheelEvent): void => {
  const target = event.currentTarget;
  if (!(target instanceof HTMLElement) || Math.abs(event.deltaY) <= Math.abs(event.deltaX)) {
    return;
  }
  target.scrollLeft += event.deltaY;
  event.preventDefault();
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

<style scoped>
.playtest-opening {
  position: relative;
  display: grid;
  min-height: 0;
  flex: 1 1 auto;
  grid-template-rows: auto minmax(20rem, 1fr) auto;
  gap: 0;
  overflow: hidden;
}

.playtest-opening-actions {
  position: relative;
  z-index: 5;
  display: grid;
  justify-items: center;
  gap: 0.8rem;
  padding: 0.75rem;
}

.playtest-opening-eyebrow {
  color: var(--playtest-text, rgba(255, 255, 255, 0.9));
  font-size: clamp(1.25rem, 2.1vw, 1.8rem);
  font-weight: 900;
}

.playtest-opening-controls {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.7rem;
}

.playtest-opening-hand-size {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  color: var(--playtest-text-muted, rgba(255, 255, 255, 0.76));
  font-size: 0.85rem;
  font-weight: 800;
}

.playtest-opening-hand {
  --playtest-opening-hand-card-width: clamp(10.75rem, 13vw, 13rem);
  position: relative;
  z-index: 4;
  display: flex;
  min-height: calc(var(--playtest-opening-hand-card-width) * 1.62);
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 1.4rem 2rem 2.1rem;
}

.playtest-opening-hand-card {
  --playtest-card-width: var(--playtest-opening-hand-card-width);
  flex: 0 0 auto;
  transform-origin: 50% 112%;
  transition:
    transform 180ms ease,
    margin 180ms ease;
}

.playtest-opening-bottom {
  box-sizing: border-box;
  position: relative;
  z-index: 6;
  display: grid;
  grid-template-columns: minmax(16rem, 1fr) minmax(0, max-content);
  gap: 0.75rem;
  min-height: calc((var(--playtest-card-width, 9.75rem) * 1.42) + 5.5rem);
  padding: 0.75rem;
  border-top: 1px solid var(--playtest-border, rgba(255, 255, 255, 0.1));
  background: var(--playtest-panel-muted, rgba(8, 10, 10, 0.64));
  backdrop-filter: blur(12px);
}

.playtest-opening-selections {
  display: grid;
  grid-template-columns: repeat(2, minmax(10rem, 1fr));
  min-width: 0;
  gap: 0;
  overflow: hidden;
  border-right: 1px solid var(--playtest-border, rgba(255, 255, 255, 0.08));
}

.playtest-opening-stacks {
  display: flex;
  min-width: 0;
  overflow-x: hidden;
  overflow-y: hidden;
  justify-content: flex-end;
  padding-bottom: 0.25rem;
}

.playtest-opening-selection-panel {
  min-height: 0;
  overflow: hidden;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.playtest-opening-selection-panel + .playtest-opening-selection-panel {
  border-left: 1px solid var(--playtest-border, rgba(255, 255, 255, 0.08));
}

.playtest-opening-selections-single {
  grid-template-columns: 1fr;
}

.playtest-opening-section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.6rem 0.8rem 0;
}

.playtest-opening-section-heading h3 {
  color: var(--playtest-text, rgba(255, 255, 255, 0.9));
  font-size: 0.95rem;
  font-weight: 900;
}

.playtest-opening-section-heading p,
.playtest-opening-section-heading span,
.playtest-opening-empty {
  color: var(--playtest-text-soft, rgba(255, 255, 255, 0.56));
  font-size: 0.78rem;
  font-weight: 700;
}

.playtest-opening-card-grid {
  display: flex;
  max-height: calc(var(--playtest-card-width, 9.75rem) * 1.95);
  gap: 0.75rem;
  overflow-x: auto;
  overflow-y: hidden;
  overscroll-behavior: contain;
  padding: 0.9rem 1.25rem 0.5rem 0.8rem;
  scroll-padding-inline: 0.8rem 1.25rem;
}

.playtest-opening-card-choice {
  position: relative;
  flex: 0 0 auto;
  border: 1px solid transparent;
  border-radius: 0.7rem;
  padding: 0.5rem;
  background: color-mix(in srgb, var(--playtest-panel-strong, white) 34%, transparent);
  text-align: left;
  transition:
    border-color 150ms ease,
    background 150ms ease,
    transform 150ms ease;
}

.playtest-opening-card-choice:hover {
  border-color: var(--playtest-border, rgba(255, 255, 255, 0.16));
  background: color-mix(in srgb, var(--playtest-panel-strong, white) 48%, transparent);
  transform: translateY(-0.08rem);
}

.playtest-opening-card-hint {
  cursor: default;
}

.playtest-opening-card-choice-selected {
  border-color: transparent;
  background: color-mix(in srgb, var(--color-accent) 24%, transparent);
}

.playtest-opening-card-choice-selected:hover {
  border-color: transparent;
  background: color-mix(in srgb, var(--color-accent) 30%, transparent);
}

@media (max-width: 900px) {
  .playtest-opening {
    overflow: auto;
  }

  .playtest-opening-hand {
    --playtest-opening-hand-card-width: clamp(9rem, 28vw, 11rem);
  }

  .playtest-opening-bottom,
  .playtest-opening-selections {
    grid-template-columns: 1fr;
  }

  .playtest-opening-stacks {
    min-width: 0;
    overflow-x: auto;
    justify-content: flex-start;
  }

  .playtest-opening-card-grid {
    max-height: none;
  }
}
</style>
