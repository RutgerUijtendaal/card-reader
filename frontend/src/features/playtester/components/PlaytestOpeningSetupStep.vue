<template>
  <section
    class="playtest-opening-setup-stage"
    :class="hasSetupCards ? '' : 'playtest-opening-setup-stage-library-only'"
  >
    <section
      v-if="hasSetupCards"
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
        <article
          v-for="group in setupGroups"
          :key="group.cardId"
          class="playtest-opening-setup-card"
          :class="
            handledSetupCardSet.has(group.cardId) ? 'playtest-opening-setup-card-handled' : ''
          "
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
              :card-back-urls-by-card-id="cardBackUrlsByCardId"
              :default-card-back-url="defaultCardBackUrl"
            />
          </div>
          <div class="playtest-opening-setup-card-main">
            <div class="playtest-opening-setup-card-title">
              <strong>{{ group.card.name }}</strong>
              <span>{{ group.instances.length }}
                {{ group.instances.length === 1 ? 'copy' : 'copies' }}</span>
            </div>
            <p class="playtest-opening-setup-rule-text">
              {{
                group.card.rules_text ||
                  'Resolve this setup effect before drawing your opening hand.'
              }}
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
    <div class="playtest-opening-setup-library-area">
      <PlaytestStackBrowser
        title="Library"
        subtitle="Set up the starting board state before drawing your hand."
        :instances="libraryInstances"
        :card-interactive="true"
        :dragging-instance-ids="draggingInstanceIds"
        :card-back-urls-by-card-id="cardBackUrlsByCardId"
        :default-card-back-url="defaultCardBackUrl"
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
        <template
          v-if="!hasSetupCards"
          #footer
        >
          <button
            class="btn-primary"
            type="button"
            @click="emit('continue-setup')"
          >
            Draw hand
          </button>
        </template>
      </PlaytestStackBrowser>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import PlaytestCard from '@/features/playtester/components/PlaytestCard.vue';
import PlaytestStackBrowser from '@/features/playtester/components/PlaytestStackBrowser.vue';
import type {
  PlaytestCardInstance,
  PlaytestCardSource,
  PlaytestHoverTarget,
  PlaytestZoneId,
} from '@/features/playtester/types';
import type { CardBackUrlsByCardId } from '@/features/playtester/utils/cardBacks';

type CardInstanceGroup = {
  cardId: string;
  card: PlaytestCardInstance['card'];
  instances: PlaytestCardInstance[];
};
const props = defineProps<{
  setupInstances: PlaytestCardInstance[];
  libraryInstances: PlaytestCardInstance[];
  handledSetupCardIds: string[];
  draggingInstanceIds: string[];
  cardBackUrlsByCardId: CardBackUrlsByCardId;
  defaultCardBackUrl: string | null;
}>();
const emit = defineEmits<{
  (e: 'continue-setup'): void;
  (e: 'toggle-setup-handled', cardId: string, handled: boolean): void;
  (e: 'move-setup-card', instanceId: string, zoneId: PlaytestZoneId): void;
  (e: 'pointer-card', instanceId: string, source: PlaytestCardSource, event: PointerEvent): void;
  (e: 'context-card', instanceId: string, event: MouseEvent): void;
  (e: 'hover', target: PlaytestHoverTarget | null): void;
}>();

const handledSetupCardSet = computed(() => new Set(props.handledSetupCardIds));
const setupGroups = computed<CardInstanceGroup[]>(() => {
  const groups = new Map<string, CardInstanceGroup>();
  for (const instance of props.setupInstances) {
    const group = groups.get(instance.cardId);
    if (group) group.instances = [...group.instances, instance];
    else
      groups.set(instance.cardId, {
        cardId: instance.cardId,
        card: instance.card,
        instances: [instance],
      });
  }
  return [...groups.values()]
    .map((group) => ({
      ...group,
      instances: [...group.instances].sort(
        (left, right) =>
          left.order - right.order || left.instanceId.localeCompare(right.instanceId),
      ),
    }))
    .sort(
      (left, right) =>
        left.card.name.localeCompare(right.card.name) || left.cardId.localeCompare(right.cardId),
    );
});
const hasSetupCards = computed(() => setupGroups.value.length > 0);
const toggleSetupHandled = (cardId: string): void => {
  emit('toggle-setup-handled', cardId, !handledSetupCardSet.value.has(cardId));
};
const emitSetupHandled = (cardId: string, event: Event): void => {
  if (event.target instanceof HTMLInputElement) {
    emit('toggle-setup-handled', cardId, event.target.checked);
  }
};
const handleCardPointer = (
  instanceId: string,
  source: PlaytestCardSource,
  event: PointerEvent,
): void => emit('pointer-card', instanceId, source, event);
const handleCardContextMenu = (instanceId: string, event: MouseEvent): void =>
  emit('context-card', instanceId, event);
</script>
