<template>
  <section
    class="playtest-stack-browser"
    :class="flush ? 'playtest-stack-browser-flush' : ''"
    :data-playtest-drop-zone="dropZoneId ?? undefined"
    :data-testid="testId"
  >
    <div class="playtest-stack-browser-header">
      <div>
        <h3>{{ title }}</h3>
        <p>{{ subtitle }}</p>
      </div>
      <div class="playtest-stack-browser-header-actions">
        <span>{{ instances.length }} {{ instances.length === 1 ? 'card' : 'cards' }}</span>
        <button
          v-if="closable"
          class="btn-secondary"
          type="button"
          @click="emit('close')"
        >
          Close
        </button>
      </div>
    </div>

    <input
      v-if="searchable"
      v-model="query"
      class="input-base playtest-stack-browser-search"
      type="search"
      :placeholder="searchPlaceholder"
    >

    <div class="playtest-stack-browser-list app-scrollbar">
      <article
        v-for="group in filteredGroups"
        :key="group.cardId"
        class="playtest-stack-browser-card"
      >
        <PlaytestCard
          :instance="group.instances[0]"
          compact
          :activatable="false"
          :card-back-url="cardBackUrl"
          :dragging="group.instances.some((instance) => draggingInstanceIds.includes(instance.instanceId))"
          :interactive="cardInteractive"
          @pointer-card="handleCardPointer"
          @context-menu="handleCardContextMenu"
          @hover="emit('hover', $event)"
        />
        <div class="playtest-stack-browser-card-main">
          <div class="playtest-stack-browser-card-title">
            <strong>{{ group.card.name }}</strong>
            <span>{{ group.instances.length }}x</span>
          </div>
          <p>{{ group.card.type_line || group.card.label }}</p>
          <div
            v-if="$slots.actions"
            class="playtest-stack-browser-actions"
          >
            <slot
              name="actions"
              :group="group"
            />
          </div>
        </div>
      </article>

      <p
        v-if="filteredGroups.length === 0"
        key="stack-browser-empty"
        class="playtest-stack-browser-empty"
      >
        {{ emptyMessage }}
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import PlaytestCard from '@/modules/playtester/components/PlaytestCard.vue';
import type {
  PlaytestCardInstance,
  PlaytestCardSource,
  PlaytestHoverTarget,
  PlaytestZoneId,
} from '@/modules/playtester/types';

export type PlaytestStackBrowserGroup = {
  cardId: string;
  card: PlaytestCardInstance['card'];
  instances: PlaytestCardInstance[];
};

const props = withDefaults(defineProps<{
  title: string;
  subtitle: string;
  instances: PlaytestCardInstance[];
  cardBackUrl?: string | null;
  cardInteractive?: boolean;
  closable?: boolean;
  draggingInstanceIds?: string[];
  dropZoneId?: PlaytestZoneId | null;
  emptyMessage?: string;
  flush?: boolean;
  searchable?: boolean;
  searchPlaceholder?: string;
  testId?: string;
}>(), {
  cardBackUrl: null,
  cardInteractive: false,
  closable: false,
  draggingInstanceIds: () => [],
  dropZoneId: null,
  emptyMessage: 'No cards match the current search.',
  flush: false,
  searchable: true,
  searchPlaceholder: 'Search stack',
  testId: 'playtest-stack-browser',
});

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'pointer-card', instanceId: string, source: PlaytestCardSource, event: PointerEvent): void;
  (e: 'context-card', instanceId: string, event: MouseEvent): void;
  (e: 'hover', target: PlaytestHoverTarget | null): void;
}>();

defineSlots<{
  actions?: (props: { group: PlaytestStackBrowserGroup }) => unknown;
}>();

const query = ref('');

const groupedInstances = computed<PlaytestStackBrowserGroup[]>(() => {
  const groups = new Map<string, PlaytestStackBrowserGroup>();
  for (const instance of props.instances) {
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
});

const filteredGroups = computed(() => {
  const search = query.value.trim().toLowerCase();
  if (!search) {
    return groupedInstances.value;
  }
  return groupedInstances.value.filter((group) =>
    [
      group.card.name,
      group.card.label,
      group.card.type_line,
      group.card.rules_text,
    ].some((value) => value.toLowerCase().includes(search)),
  );
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
.playtest-stack-browser {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--playtest-border);
  border-radius: 0.9rem;
  background: var(--playtest-panel-strong);
  box-shadow: 0 2rem 5rem color-mix(in srgb, var(--color-shadow) 20%, transparent);
  animation: playtest-stack-browser-in 170ms ease-out;
}

.playtest-stack-browser-flush {
  height: 100%;
}

.playtest-stack-browser-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  border-bottom: 1px solid var(--playtest-border);
  padding: 1rem;
}

.playtest-stack-browser-header h3 {
  color: var(--playtest-text);
  font-size: 1rem;
  font-weight: 900;
}

.playtest-stack-browser-header p,
.playtest-stack-browser-header span,
.playtest-stack-browser-empty,
.playtest-stack-browser-card p {
  color: var(--playtest-text-soft);
  font-size: 0.78rem;
  font-weight: 700;
}

.playtest-stack-browser-header-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.75rem;
}

.playtest-stack-browser-search {
  width: calc(100% - 2rem);
  margin: 1rem;
}

.playtest-stack-browser-list {
  display: grid;
  min-height: 0;
  gap: 0.75rem;
  overflow: auto;
  padding: 0 1rem 1rem;
}

.playtest-stack-browser-card {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  gap: 0.7rem;
  border-top: 1px solid color-mix(in srgb, var(--playtest-border) 72%, transparent);
  padding-top: 0.75rem;
  transition:
    border-color 150ms ease,
    opacity 160ms ease,
    transform 160ms ease;
}

.playtest-stack-browser-card:hover {
  border-top-color: color-mix(in srgb, var(--color-accent) 42%, var(--playtest-border));
  transform: translateX(0.12rem);
}

.playtest-stack-browser-card-main {
  display: grid;
  flex: 1 1 auto;
  min-width: 0;
  gap: 0.45rem;
}

.playtest-stack-browser-card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
  color: var(--playtest-text);
  font-size: 0.9rem;
  font-weight: 900;
}

.playtest-stack-browser-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  gap: 0.35rem;
}

.playtest-stack-browser-list-enter-active,
.playtest-stack-browser-list-leave-active {
  transition:
    opacity 160ms ease,
    transform 160ms ease,
    filter 160ms ease;
}

.playtest-stack-browser-list-enter-from,
.playtest-stack-browser-list-leave-to {
  opacity: 0;
  filter: blur(0.1rem);
  transform: translateY(0.3rem);
}

.playtest-stack-browser-list-move {
  transition: transform 180ms ease;
}

@keyframes playtest-stack-browser-in {
  from {
    opacity: 0;
    transform: translateY(0.4rem) scale(0.992);
  }

  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .playtest-stack-browser,
  .playtest-stack-browser *,
  .playtest-stack-browser-list-enter-active,
  .playtest-stack-browser-list-leave-active,
  .playtest-stack-browser-list-move {
    animation-duration: 1ms !important;
    transition-duration: 1ms !important;
  }
}
</style>
