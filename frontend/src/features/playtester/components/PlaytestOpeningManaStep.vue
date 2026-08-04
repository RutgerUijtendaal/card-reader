<template>
  <section
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
            :class="
              selectedManaSet.has(instance.instanceId)
                ? 'playtest-opening-copy-button-selected'
                : ''
            "
            type="button"
            :aria-pressed="selectedManaSet.has(instance.instanceId)"
            @click.stop="
              emit('toggle-mana', instance.instanceId, !selectedManaSet.has(instance.instanceId))
            "
            @contextmenu.prevent.stop="
              emit('toggle-mana', instance.instanceId, !selectedManaSet.has(instance.instanceId))
            "
          >
            {{ index + 1 }}
          </button>
        </div>
      </article>
    </div>
    <div class="playtest-opening-mana-actions">
      <button
        :class="hasSetupCards ? 'btn-primary' : 'btn-secondary'"
        type="button"
        :disabled="selectedManaIds.length !== STARTING_MANA_REQUIRED"
        @click="emit('continue-mana')"
      >
        Setup board
      </button>
      <button
        v-if="!hasSetupCards"
        class="btn-primary"
        type="button"
        :disabled="selectedManaIds.length !== STARTING_MANA_REQUIRED"
        @click="emit('draw-hand')"
      >
        Draw hand
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import PlaytestCard from '@/features/playtester/components/PlaytestCard.vue';
import { STARTING_MANA_REQUIRED } from '@/features/playtester/playtestStateCore';
import type { PlaytestCardInstance } from '@/features/playtester/types';

type CardInstanceGroup = { cardId: string; instances: PlaytestCardInstance[] };

const props = defineProps<{
  manaInstances: PlaytestCardInstance[];
  selectedManaIds: string[];
  hasSetupCards: boolean;
}>();
const emit = defineEmits<{
  (e: 'continue-mana'): void;
  (e: 'draw-hand'): void;
  (e: 'toggle-mana', instanceId: string, selected: boolean): void;
}>();

const selectedManaSet = computed(() => new Set(props.selectedManaIds));
const manaGroups = computed<CardInstanceGroup[]>(() => {
  const groups = new Map<string, PlaytestCardInstance[]>();
  for (const instance of props.manaInstances) {
    groups.set(instance.cardId, [...(groups.get(instance.cardId) ?? []), instance]);
  }
  return [...groups.entries()]
    .map(([cardId, instances]) => ({
      cardId,
      instances: [...instances].sort(
        (left, right) =>
          left.order - right.order || left.instanceId.localeCompare(right.instanceId),
      ),
    }))
    .sort(
      (left, right) =>
        left.instances[0].card.name.localeCompare(right.instances[0].card.name) ||
        left.cardId.localeCompare(right.cardId),
    );
});
const selectManaFromGroup = (group: CardInstanceGroup): void => {
  const instance = group.instances.find((entry) => !selectedManaSet.value.has(entry.instanceId));
  if (instance) emit('toggle-mana', instance.instanceId, true);
};
const deselectManaFromGroup = (group: CardInstanceGroup): void => {
  const instance = [...group.instances]
    .reverse()
    .find((entry) => selectedManaSet.value.has(entry.instanceId));
  if (instance) emit('toggle-mana', instance.instanceId, false);
};
</script>
