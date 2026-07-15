<template>
  <section
    class="space-y-5"
    data-testid="deck-mana-distribution"
  >
    <div class="flex items-start justify-between gap-3">
      <div>
        <h3 class="theme-section-title text-base font-semibold">
          Mana distribution
        </h3>
        <p class="theme-section-muted mt-1 text-xs">
          Colored costs across {{ summary.totalCards }} non-mana {{ summary.totalCards === 1 ? 'card' : 'cards' }}.
        </p>
      </div>
      <button
        class="btn-secondary h-8 px-2.5 text-xs"
        type="button"
        @click="groupManagerOpen = true"
      >
        Manage groups
      </button>
    </div>

    <div
      v-if="summary.colors.length === 0"
      class="theme-empty-state px-3 py-5 text-xs"
    >
      No colored mana costs were found on this board.
    </div>

    <template v-else>
      <DeckManaStatisticsSection
        title="All cards"
        :total-cards="summary.totalCards"
        :colors="summary.colors"
      />

      <div
        v-if="summary.groups.length > 0"
        class="space-y-5"
      >
        <DeckManaStatisticsSection
          v-for="groupSummary in summary.groups"
          :key="groupSummary.group.id"
          :title="groupSummary.group.name"
          :total-cards="groupSummary.totalCards"
          :colors="groupSummary.colors"
        />
      </div>
      <p
        v-else
        class="theme-section-muted theme-divider border-t pt-4 text-xs"
      >
        Add named type groups to compare subsets of this board.
      </p>
    </template>

    <DeckManaTypeGroupsDialog
      :open="groupManagerOpen"
      :groups="groups"
      :types="types"
      @close="groupManagerOpen = false"
      @save="saveTypeGroups"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import {
  buildManaDistribution,
  type ManaDistributionCardLike,
  type ManaDistributionEntryLike,
  type ManaDistributionSymbolLike,
  type ManaTypeGroup,
} from '@/composables/decks/manaDistribution';
import { useManaTypeGroups } from '@/composables/decks/useManaTypeGroups';
import DeckManaStatisticsSection from '@/modules/decks/components/DeckManaStatisticsSection.vue';
import DeckManaTypeGroupsDialog from '@/modules/decks/components/DeckManaTypeGroupsDialog.vue';
import type { DeckMetadataOption } from '@/modules/decks/types';

const props = defineProps<{
  entries: ManaDistributionEntryLike<ManaDistributionCardLike>[];
  symbols: ManaDistributionSymbolLike[];
  types: DeckMetadataOption[];
}>();

const { groups, saveGroups } = useManaTypeGroups();
const groupManagerOpen = ref(false);
const summary = computed(() => buildManaDistribution(props.entries, props.symbols, groups.value));

const saveTypeGroups = (nextGroups: ManaTypeGroup[]): void => {
  saveGroups(nextGroups);
  groupManagerOpen.value = false;
};
</script>
