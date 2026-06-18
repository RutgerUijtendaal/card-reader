<template>
  <section
    class="playtest-opening"
    data-testid="playtest-opening-setup"
  >
    <header class="playtest-opening-header">
      <div class="playtest-opening-step-nav">
        <button
          class="playtest-opening-step-nav-button"
          type="button"
          :disabled="!canGoPrevious"
          aria-label="Previous step"
          @click="emit('previous-step')"
        >
          <ArrowLeft aria-hidden="true" />
        </button>

        <div class="playtest-opening-steps">
          <button
            v-for="step in visibleSteps"
            :key="step.id"
            class="playtest-opening-step"
            :class="[
              step.id === openingStep ? 'playtest-opening-step-active' : '',
              stepComplete(step.id) ? 'playtest-opening-step-complete' : '',
            ]"
            type="button"
            :disabled="!canSelectStep(step.id)"
            :aria-current="step.id === openingStep ? 'step' : undefined"
            @click="selectStep(step.id)"
          >
            <span>{{ step.index }}</span>
            <strong>{{ step.label }}</strong>
          </button>
        </div>

        <button
          class="playtest-opening-step-nav-button"
          type="button"
          :disabled="!canGoNext"
          aria-label="Next step"
          @click="goNext"
        >
          <ArrowRight aria-hidden="true" />
        </button>
      </div>
    </header>

    <div class="playtest-opening-main">
      <section
        v-if="openingStep === 'mana'"
        key="mana"
        class="playtest-opening-panel playtest-opening-mana"
        data-testid="playtest-opening-mana"
      >
        <div class="playtest-opening-panel-heading">
          <div>
            <h3>Starting mana</h3>
            <p>Select exactly 3 mana copies that should begin in play.</p>
          </div>
        </div>

        <div class="playtest-opening-mana-grid app-scrollbar">
          <article
            v-for="group in manaGroups"
            :key="group.cardId"
            class="playtest-opening-mana-card"
            role="button"
            tabindex="0"
            @click="selectManaFromGroup(group)"
            @keydown.enter.prevent="selectManaFromGroup(group)"
            @keydown.space.prevent="selectManaFromGroup(group)"
            @contextmenu.prevent="deselectManaFromGroup(group)"
          >
            <PlaytestCard
              :instance="group.instances[0]"
              :interactive="false"
            />
            <div class="playtest-opening-card-copy-actions">
              <button
                v-for="(instance, index) in group.instances"
                :key="instance.instanceId"
                class="playtest-opening-copy-button"
                :class="selectedManaSet.has(instance.instanceId) ? 'playtest-opening-copy-button-selected' : ''"
                type="button"
                :aria-pressed="selectedManaSet.has(instance.instanceId)"
                @click.stop="emit('toggle-mana', instance.instanceId, !selectedManaSet.has(instance.instanceId))"
                @contextmenu.prevent.stop="emit('toggle-mana', instance.instanceId, !selectedManaSet.has(instance.instanceId))"
              >
                {{ index + 1 }}
              </button>
            </div>
          </article>
        </div>

        <button
          class="btn-primary playtest-opening-mana-accept"
          type="button"
          :disabled="selectedManaIds.length !== STARTING_MANA_REQUIRED"
          @click="emit('continue-mana')"
        >
          Accept
        </button>
      </section>

      <section
        v-else-if="openingStep === 'setup'"
        key="setup"
        class="playtest-opening-setup-stage"
      >
        <section
          class="playtest-opening-panel playtest-opening-setup-guide"
          data-testid="playtest-opening-setup-cards"
        >
          <div class="playtest-opening-panel-heading">
            <div>
              <h3>Setup instructions</h3>
              <p>Ready your board state here: move cards between zones before drawing your hand.</p>
            </div>
            <span>{{ setupGroups.length }} found</span>
          </div>

          <div class="playtest-opening-setup-list app-scrollbar">
            <div
              v-if="setupGroups.length === 0"
              key="setup-empty"
              class="playtest-opening-empty"
            >
              No cards with Setup tags found.
            </div>
            <article
              v-for="group in setupGroups"
              :key="group.cardId"
              class="playtest-opening-setup-card"
              :class="handledSetupCardSet.has(group.cardId) ? 'playtest-opening-setup-card-handled' : ''"
              role="checkbox"
              tabindex="0"
              :aria-checked="handledSetupCardSet.has(group.cardId)"
              @click="toggleSetupHandled(group.cardId)"
              @keydown.enter.prevent="toggleSetupHandled(group.cardId)"
              @keydown.space.prevent="toggleSetupHandled(group.cardId)"
            >
              <div class="playtest-opening-setup-card-preview">
                <PlaytestCard
                  :instance="group.instances[0]"
                  :interactive="false"
                />
              </div>
              <div class="playtest-opening-setup-card-main">
                <div class="playtest-opening-setup-card-title">
                  <strong>{{ group.card.name }}</strong>
                  <span>{{ group.instances.length }} {{ group.instances.length === 1 ? 'copy' : 'copies' }}</span>
                </div>
                <p class="playtest-opening-setup-rule-text">
                  {{ group.card.rules_text || 'Resolve this setup effect before drawing your opening hand.' }}
                </p>
                <label
                  class="playtest-opening-setup-check"
                  @click.stop
                >
                  <input
                    type="checkbox"
                    :checked="handledSetupCardSet.has(group.cardId)"
                    @change="emitSetupHandled(group.cardId, $event)"
                  >
                  <span>Handled</span>
                </label>
              </div>
            </article>
          </div>

          <div class="playtest-opening-setup-footer">
            <button
              class="btn-primary"
              type="button"
              @click="emit('continue-setup')"
            >
              Draw hand
            </button>
          </div>
        </section>

        <PlaytestStackBrowser
          title="Library"
          subtitle="Move one copy at a time while resolving setup."
          :instances="libraryInstances"
          :card-interactive="true"
          :dragging-instance-ids="draggingInstanceIds"
          drop-zone-id="library"
          search-placeholder="Search library"
          test-id="playtest-opening-library-browser"
          @pointer-card="handleCardPointer"
          @context-card="handleCardContextMenu"
          @hover="emit('hover', $event)"
        >
          <template #actions="{ group }">
            <button
              class="btn-primary"
              type="button"
              @click="emit('move-setup-card', group.instances[0].instanceId, 'banish')"
            >
              Banish
            </button>
            <button
              class="btn-secondary"
              type="button"
              @click="emit('move-setup-card', group.instances[0].instanceId, 'discard')"
            >
              Discard
            </button>
            <button
              class="btn-secondary"
              type="button"
              @click="emit('move-setup-card', group.instances[0].instanceId, 'play')"
            >
              Play
            </button>
          </template>
        </PlaytestStackBrowser>
      </section>

      <section
        v-else
        key="hand"
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
            key="opening-hand-empty"
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
    </div>

    <div
      ref="bottomRef"
      class="playtest-opening-bottom"
    >
      <section
        class="playtest-opening-picked-mana"
        :class="selectedManaInstances.length === 0 ? 'playtest-opening-picked-mana-empty' : ''"
        data-testid="playtest-opening-picked-mana"
      >
        <div class="playtest-opening-picked-mana-bar">
          <span>{{ bottomZoneLabel }}</span>
        </div>
        <div class="playtest-opening-picked-mana-fan">
          <div
            v-for="(instance, index) in bottomZoneInstances"
            :key="instance.instanceId"
            class="playtest-opening-picked-mana-card"
            :style="bottomFanCardStyle(index, bottomZoneInstances.length)"
          >
            <PlaytestCard
              :instance="instance"
              :dragging="draggingInstanceIds.includes(instance.instanceId)"
              :interactive="isBottomInstanceDraggable(instance)"
              @pointer-card="handleCardPointer"
              @context-menu="handleCardContextMenu"
              @hover="emit('hover', $event)"
            />
          </div>
          <span
            v-if="bottomZoneInstances.length === 0"
            key="bottom-placeholder"
            class="playtest-opening-picked-mana-placeholder"
          />
        </div>
      </section>
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
import { ArrowLeft, ArrowRight } from 'lucide-vue-next';
import PlaytestCard from '@/modules/playtester/components/PlaytestCard.vue';
import PlaytestStackBrowser from '@/modules/playtester/components/PlaytestStackBrowser.vue';
import { STARTING_MANA_REQUIRED } from '@/modules/playtester/playtestState';
import type {
  PlaytestCardInstance,
  PlaytestCardSource,
  PlaytestHoverTarget,
  PlaytestOpeningStep,
  PlaytestZoneId,
} from '@/modules/playtester/types';

type CardInstanceGroup = {
  cardId: string;
  card: PlaytestCardInstance['card'];
  instances: PlaytestCardInstance[];
};

const props = defineProps<{
  openingStep: PlaytestOpeningStep;
  handInstances: PlaytestCardInstance[];
  manaInstances: PlaytestCardInstance[];
  setupInstances: PlaytestCardInstance[];
  stagedPlayInstances: PlaytestCardInstance[];
  libraryInstances: PlaytestCardInstance[];
  selectedManaIds: string[];
  handledSetupCardIds: string[];
  handSize: number;
  mulliganCount: number;
  draggingInstanceIds: string[];
}>();

const emit = defineEmits<{
  (e: 'continue-mana'): void;
  (e: 'continue-setup'): void;
  (e: 'previous-step'): void;
  (e: 'select-step', step: PlaytestOpeningStep): void;
  (e: 'keep'): void;
  (e: 'mulligan'): void;
  (e: 'update-hand-size', handSize: number): void;
  (e: 'toggle-mana', instanceId: string, selected: boolean): void;
  (e: 'toggle-setup-handled', cardId: string, handled: boolean): void;
  (e: 'move-setup-card', instanceId: string, zoneId: PlaytestZoneId): void;
  (e: 'pointer-card', instanceId: string, source: PlaytestCardSource, event: PointerEvent): void;
  (e: 'context-card', instanceId: string, event: MouseEvent): void;
  (e: 'hover', target: PlaytestHoverTarget | null): void;
  (e: 'bottom-resize', width: number, height: number): void;
}>();

const bottomRef = ref<HTMLElement | null>(null);
const selectedManaSet = computed(() => new Set(props.selectedManaIds));
const handledSetupCardSet = computed(() => new Set(props.handledSetupCardIds));

const groupInstancesByCard = (instances: PlaytestCardInstance[]): CardInstanceGroup[] => {
  const groups = new Map<string, CardInstanceGroup>();
  for (const instance of instances) {
    const group = groups.get(instance.cardId);
    if (group) {
      group.instances = [...group.instances, instance];
    } else {
      groups.set(instance.cardId, {
        cardId: instance.cardId,
        card: instance.card,
        instances: [instance],
      });
    }
  }
  return [...groups.values()]
    .map((group) => ({
      ...group,
      instances: [...group.instances].sort((left, right) => left.order - right.order || left.instanceId.localeCompare(right.instanceId)),
    }))
    .sort((left, right) => left.card.name.localeCompare(right.card.name) || left.cardId.localeCompare(right.cardId));
};

const manaGroups = computed(() => groupInstancesByCard(props.manaInstances));
const setupGroups = computed(() => groupInstancesByCard(props.setupInstances));
const selectedManaInstances = computed(() => {
  const selectedIds = new Set(props.selectedManaIds);
  return props.manaInstances.filter((instance) => selectedIds.has(instance.instanceId));
});
const setupHandInstances = computed(() =>
  props.openingStep === 'setup' ? props.handInstances : [],
);
const bottomZoneInstances = computed(() => [
  ...selectedManaInstances.value,
  ...props.stagedPlayInstances,
  ...setupHandInstances.value,
]);
const stagedPlayInstanceIds = computed(() =>
  new Set(props.stagedPlayInstances.map((instance) => instance.instanceId)),
);
const bottomZoneLabel = computed(() => {
  const segments = ['Picked mana'];
  if (props.stagedPlayInstances.length > 0) {
    segments.push(`Play ${props.stagedPlayInstances.length}`);
  }
  if (setupHandInstances.value.length > 0) {
    segments.push(`Hand ${setupHandInstances.value.length}`);
  }
  return segments.join(' / ');
});

const isBottomInstanceDraggable = (instance: PlaytestCardInstance): boolean =>
  props.openingStep === 'setup' && (
    ['hand', 'hero', 'library', 'discard', 'banish'].includes(instance.zoneId)
    || stagedPlayInstanceIds.value.has(instance.instanceId)
  );

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
const visibleSteps = computed(() => {
  const steps: Array<{ id: PlaytestOpeningStep; label: string }> = [
    { id: 'mana', label: 'Mana' },
    { id: 'setup', label: 'Setup' },
    { id: 'hand', label: 'Hand' },
  ];
  return steps.map((step, index) => ({
    ...step,
    index: index + 1,
  }));
});

const currentStepIndex = computed(() =>
  visibleSteps.value.findIndex((step) => step.id === props.openingStep),
);
const canGoPrevious = computed(() => currentStepIndex.value > 0);
const canGoNext = computed(() => {
  if (props.openingStep === 'mana') {
    return props.selectedManaIds.length === STARTING_MANA_REQUIRED;
  }
  return props.openingStep === 'setup';
});

const stepComplete = (step: PlaytestOpeningStep): boolean => {
  const order = visibleSteps.value.findIndex((entry) => entry.id === step);
  const current = visibleSteps.value.findIndex((entry) => entry.id === props.openingStep);
  return order >= 0 && current > order;
};

const canSelectStep = (step: PlaytestOpeningStep): boolean => {
  const order = visibleSteps.value.findIndex((entry) => entry.id === step);
  return order >= 0 && order < currentStepIndex.value;
};

const selectStep = (step: PlaytestOpeningStep): void => {
  if (canSelectStep(step)) {
    emit('select-step', step);
  }
};

const selectManaFromGroup = (group: CardInstanceGroup): void => {
  const instance = group.instances.find((entry) => !selectedManaSet.value.has(entry.instanceId));
  if (instance) {
    emit('toggle-mana', instance.instanceId, true);
  }
};

const deselectManaFromGroup = (group: CardInstanceGroup): void => {
  const instance = [...group.instances].reverse().find((entry) => selectedManaSet.value.has(entry.instanceId));
  if (instance) {
    emit('toggle-mana', instance.instanceId, false);
  }
};

const emitSetupHandled = (cardId: string, event: Event): void => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) {
    return;
  }
  emit('toggle-setup-handled', cardId, target.checked);
};

const toggleSetupHandled = (cardId: string): void => {
  emit('toggle-setup-handled', cardId, !handledSetupCardSet.value.has(cardId));
};

const goNext = (): void => {
  if (!canGoNext.value) {
    return;
  }
  if (props.openingStep === 'setup') {
    emit('continue-setup');
    return;
  }
  emit('continue-mana');
};

useResizeObserver(bottomRef, ([entry]) => {
  emit('bottom-resize', entry?.contentRect.width ?? 0, entry?.contentRect.height ?? 0);
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

const openingHandCardStyle = (index: number, total: number): Record<string, string | number> => {
  const center = index - (total - 1) / 2;
  return {
    marginLeft: index === 0 ? '0' : 'calc(var(--playtest-card-width) * -0.34)',
    transform: `translateY(${center * center * 0.3}rem) rotate(${center * 5.2}deg)`,
    transformOrigin: '50% 112%',
    zIndex: 30 + index,
  };
};

const bottomFanCardStyle = (index: number, total: number): Record<string, string | number> => {
  const center = index - (total - 1) / 2;
  return {
    marginLeft: index === 0 ? '0' : 'calc(var(--playtest-card-width) * -0.42)',
    transform: `translateY(${Math.abs(center) * 0.32}rem) rotate(${center * 3.8}deg)`,
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
  overflow: hidden;
}

.playtest-opening-header {
  position: relative;
  z-index: 7;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 1rem;
  padding: 0.75rem;
  text-align: center;
}

.playtest-opening-steps {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.playtest-opening-step-nav {
  display: inline-grid;
  grid-template-columns: 2.25rem minmax(0, auto) 2.25rem;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.playtest-opening-step-nav-button {
  display: grid;
  width: 2.25rem;
  height: 2.25rem;
  place-items: center;
  border: 1px solid var(--playtest-border);
  border-radius: 999px;
  background: color-mix(in srgb, var(--playtest-panel-strong) 38%, transparent);
  color: var(--playtest-text);
  transition:
    background-color 150ms ease,
    border-color 150ms ease,
    color 150ms ease,
    opacity 150ms ease,
    transform 150ms ease;
}

.playtest-opening-step-nav-button svg {
  width: 1rem;
  height: 1rem;
}

.playtest-opening-step-nav-button:disabled {
  cursor: default;
  opacity: 0.38;
}

.playtest-opening-step-nav-button:not(:disabled):hover,
.playtest-opening-step-nav-button:not(:disabled):focus-visible {
  border-color: color-mix(in srgb, var(--color-accent) 58%, var(--playtest-border));
  background: color-mix(in srgb, var(--color-accent) 18%, var(--playtest-panel-strong));
  transform: translateY(-0.08rem);
}

.playtest-opening-step {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  border: 0;
  background: transparent;
  color: var(--playtest-text-soft);
  cursor: pointer;
  font-size: 0.78rem;
  font-weight: 400;
  padding: 0;
  transition:
    color 150ms ease,
    opacity 150ms ease;
}

.playtest-opening-step:disabled {
  cursor: default;
}

.playtest-opening-step span {
  display: grid;
  width: 1.55rem;
  height: 1.55rem;
  place-items: center;
  border: 1px solid var(--playtest-border);
  border-radius: 999px;
  background: color-mix(in srgb, var(--playtest-panel-strong) 42%, transparent);
  transition:
    background-color 170ms ease,
    border-color 170ms ease,
    transform 170ms ease;
}

.playtest-opening-step-active {
  color: var(--playtest-text);
}

.playtest-opening-step-active span,
.playtest-opening-step-complete span {
  border-color: color-mix(in srgb, var(--color-accent) 62%, var(--playtest-border));
  background: color-mix(in srgb, var(--color-accent) 22%, transparent);
}

.playtest-opening-step:not(:disabled):hover span,
.playtest-opening-step:not(:disabled):focus-visible span {
  transform: translateY(-0.08rem);
}

.playtest-opening-stage-enter-active,
.playtest-opening-stage-leave-active {
  transition:
    opacity 180ms ease,
    transform 180ms ease,
    filter 180ms ease;
}

.playtest-opening-stage-enter-from {
  opacity: 0;
  filter: blur(0.2rem);
  transform: translateY(0.6rem) scale(0.992);
}

.playtest-opening-stage-leave-to {
  opacity: 0;
  filter: blur(0.16rem);
  transform: translateY(-0.45rem) scale(0.996);
}

.playtest-opening-hand-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.playtest-opening-hand-size {
  color: var(--playtest-text-muted);
  font-size: 0.85rem;
  font-weight: 800;
}

.playtest-opening-hand-size {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
}

.playtest-opening-main {
  position: relative;
  z-index: 4;
  display: grid;
  min-height: 0;
  gap: 0.85rem;
  padding: 0.75rem 1rem 1rem;
}

.playtest-opening-panel {
  min-height: 0;
  overflow: hidden;
}

.playtest-opening-mana {
  display: grid;
  min-height: 0;
  align-content: center;
  justify-items: center;
  gap: 1rem;
  overflow: visible;
}

.playtest-opening-panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.2rem 0.2rem 0.65rem;
}

.playtest-opening-panel-heading h3,
.playtest-opening-hand-stage h3 {
  color: var(--playtest-text);
  font-size: 1rem;
  font-weight: 900;
}

.playtest-opening-panel-heading p,
.playtest-opening-panel-heading span,
.playtest-opening-empty {
  color: var(--playtest-text-soft);
  font-size: 0.78rem;
  font-weight: 700;
}

.playtest-opening-mana .playtest-opening-panel-heading {
  width: min(100%, 72rem);
  align-items: center;
  padding-bottom: 0;
  text-align: center;
}

.playtest-opening-mana .playtest-opening-panel-heading > div {
  display: grid;
  flex: 1 1 auto;
  justify-items: center;
}

.playtest-opening-mana-grid {
  display: flex;
  width: min(100%, 78rem);
  max-height: min(34rem, 58vh);
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: center;
  gap: 0.85rem;
  overflow: auto;
  padding: 0.25rem max(0.5rem, 2vw) 0.75rem;
}

.playtest-opening-mana-card,
.playtest-opening-setup-card {
  display: flex;
  gap: 0.7rem;
  min-width: 0;
}

.playtest-opening-mana-card {
  flex: 0 0 var(--playtest-card-width, 9.75rem);
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition:
    opacity 170ms ease,
    transform 170ms ease,
    filter 170ms ease;
}

.playtest-opening-mana-card:hover,
.playtest-opening-mana-card:focus-visible {
  filter: brightness(1.05);
  transform: translateY(-0.18rem);
}

.playtest-opening-card-copy-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.35rem;
}

.playtest-opening-copy-button {
  display: grid;
  width: 1.8rem;
  height: 1.8rem;
  place-items: center;
  border: 1px solid var(--playtest-border);
  border-radius: 999px;
  background: color-mix(in srgb, var(--playtest-panel-strong) 36%, transparent);
  color: var(--playtest-text-muted);
  font-size: 0.78rem;
  font-weight: 900;
  transition:
    background-color 140ms ease,
    border-color 140ms ease,
    color 140ms ease,
    transform 140ms ease;
}

.playtest-opening-copy-button-selected {
  border-color: color-mix(in srgb, var(--color-accent) 70%, var(--playtest-border));
  background: color-mix(in srgb, var(--color-accent) 26%, transparent);
  color: var(--playtest-text);
  transform: translateY(-0.08rem);
}

.playtest-opening-mana-accept {
  min-width: 8rem;
}

.playtest-opening-setup-stage {
  display: grid;
  width: min(100%, 96rem);
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  min-height: 0;
  align-items: stretch;
  justify-content: center;
  justify-self: center;
}

.playtest-opening-setup-guide {
  min-height: 0;
}

.playtest-opening-setup-guide {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  align-content: stretch;
}

.playtest-opening-setup-list {
  display: grid;
  gap: 0.75rem;
  overflow: auto;
  align-content: start;
  padding: 1rem 0.35rem 0.5rem 0.2rem;
}

.playtest-opening-setup-footer {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid color-mix(in srgb, var(--playtest-border) 72%, transparent);
  padding: 0.85rem 0.2rem 0;
}

.playtest-opening-setup-card {
  align-items: flex-start;
  border-top: 1px solid color-mix(in srgb, var(--playtest-border) 72%, transparent);
  padding-top: 0.75rem;
}

.playtest-opening-setup-card {
  display: grid;
  grid-template-columns: var(--playtest-card-width, 9.75rem) minmax(0, 1fr);
  gap: 1rem;
  cursor: pointer;
  padding-right: 0.2rem;
  transition:
    border-color 160ms ease,
    opacity 160ms ease,
    transform 160ms ease;
}

.playtest-opening-setup-card:hover,
.playtest-opening-setup-card:focus-visible {
  border-top-color: color-mix(in srgb, var(--color-accent) 54%, var(--playtest-border));
  transform: translateX(0.16rem);
}

.playtest-opening-setup-card-handled {
  opacity: 0.72;
}

.playtest-opening-setup-card-preview {
  width: var(--playtest-card-width, 9.75rem);
  min-width: var(--playtest-card-width, 9.75rem);
}

.playtest-opening-setup-card-main {
  display: grid;
  min-width: 0;
  align-content: start;
  gap: 0.55rem;
}

.playtest-opening-setup-card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
  color: var(--playtest-text);
  font-size: 0.9rem;
  font-weight: 900;
}

.playtest-opening-setup-rule-text {
  border: 1px solid color-mix(in srgb, var(--playtest-border) 76%, transparent);
  border-radius: 0.65rem;
  background: color-mix(in srgb, var(--playtest-panel-strong) 62%, transparent);
  color: var(--playtest-text);
  font-size: 0.86rem;
  font-weight: 400;
  line-height: 1.55;
  overflow-wrap: anywhere;
  padding: 0.75rem 0.85rem;
  transition:
    background-color 160ms ease,
    border-color 160ms ease;
}

.playtest-opening-setup-card-handled .playtest-opening-setup-rule-text {
  border-color: color-mix(in srgb, var(--color-accent) 44%, var(--playtest-border));
  background: color-mix(in srgb, var(--color-accent) 10%, var(--playtest-panel-strong));
}

.playtest-opening-setup-check {
  display: inline-flex;
  width: max-content;
  align-items: center;
  gap: 0.45rem;
  color: var(--playtest-text);
  font-size: 0.82rem;
  font-weight: 900;
}

.playtest-opening-setup-check input {
  width: 1rem;
  height: 1rem;
  accent-color: var(--color-accent);
}

.playtest-opening-hand-stage {
  display: grid;
  align-content: center;
  justify-items: center;
  min-height: 0;
  gap: 1rem;
}

.playtest-opening-hand {
  --playtest-opening-hand-card-width: clamp(10.75rem, 13vw, 13rem);
  position: relative;
  display: flex;
  width: min(100%, 78rem);
  min-height: calc(var(--playtest-opening-hand-card-width) * 1.62);
  align-items: center;
  justify-content: center;
  overflow: visible;
  padding: 1.4rem 2rem 2.1rem;
}

.playtest-opening-hand-actions {
  width: min(100%, 78rem);
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
  display: flex;
  align-items: stretch;
  gap: 0.75rem;
  min-height: calc((var(--playtest-card-width, 9.75rem) * 1.42) + 5.5rem);
  border-top: 1px solid color-mix(in srgb, var(--playtest-border) 82%, transparent);
  background: color-mix(in srgb, var(--playtest-surface) 42%, transparent);
  padding: 0.75rem;
  box-shadow: 0 -0.75rem 1.5rem color-mix(in srgb, var(--color-shadow) 16%, transparent);
}

.playtest-opening-picked-mana {
  flex: 1 1 24rem;
  min-width: 0;
  overflow: visible;
  border-right: 1px solid var(--playtest-border);
}

.playtest-opening-picked-mana-empty {
  border-right-color: color-mix(in srgb, var(--playtest-border) 42%, transparent);
}

.playtest-opening-picked-mana-bar {
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

.playtest-opening-picked-mana-empty .playtest-opening-picked-mana-bar {
  visibility: hidden;
}

.playtest-opening-picked-mana-fan {
  display: flex;
  box-sizing: border-box;
  height: calc((var(--playtest-card-width, 9.75rem) * 1.42) + 2rem);
  min-width: max-content;
  align-items: flex-end;
  justify-content: center;
  padding: 1rem 1.25rem 0.65rem;
}

.playtest-opening-picked-mana-placeholder {
  display: block;
  width: var(--playtest-card-width, 9.75rem);
  aspect-ratio: 63 / 88;
  visibility: hidden;
}

.playtest-opening-picked-mana-card {
  flex: 0 0 auto;
  transition:
    transform 180ms ease,
    margin 180ms ease,
    opacity 160ms ease,
    filter 160ms ease;
}

.playtest-card-list-enter-active,
.playtest-card-list-leave-active {
  transition:
    opacity 170ms ease,
    transform 170ms ease,
    filter 170ms ease;
}

.playtest-card-list-enter-from,
.playtest-card-list-leave-to {
  opacity: 0;
  filter: blur(0.12rem);
  transform: translateY(0.35rem) scale(0.98);
}

.playtest-card-list-move {
  transition: transform 180ms ease;
}

.playtest-hand-fan-enter-active,
.playtest-hand-fan-leave-active {
  transition:
    opacity 170ms ease,
    filter 170ms ease;
}

.playtest-hand-fan-enter-from,
.playtest-hand-fan-leave-to {
  opacity: 0;
  filter: blur(0.12rem);
}

.playtest-hand-fan-move {
  transition:
    transform 190ms ease,
    margin 190ms ease;
}

.playtest-opening-stacks {
  display: flex;
  flex: 0 1 auto;
  min-width: 0;
  overflow-x: hidden;
  overflow-y: hidden;
  justify-content: flex-end;
  padding-bottom: 0.25rem;
}

@media (max-width: 900px) {
  .playtest-opening {
    overflow: auto;
  }

  .playtest-opening-header,
  .playtest-opening-hand-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .playtest-opening-main {
    grid-template-columns: 1fr;
  }

  .playtest-opening-setup-stage {
    grid-template-columns: 1fr;
  }

  .playtest-opening-setup-card {
    grid-template-columns: var(--playtest-card-width, 9.75rem) minmax(0, 1fr);
  }

  .playtest-opening-hand {
    --playtest-opening-hand-card-width: clamp(9rem, 28vw, 11rem);
  }

  .playtest-opening-stacks {
    min-width: 0;
    overflow-x: auto;
    justify-content: flex-start;
  }
}

@media (prefers-reduced-motion: reduce) {
  .playtest-opening *,
  .playtest-opening-stage-enter-active,
  .playtest-opening-stage-leave-active,
  .playtest-card-list-enter-active,
  .playtest-card-list-leave-active,
  .playtest-card-list-move,
  .playtest-hand-fan-enter-active,
  .playtest-hand-fan-leave-active,
  .playtest-hand-fan-move {
    animation-duration: 1ms !important;
    transition-duration: 1ms !important;
  }
}
</style>
