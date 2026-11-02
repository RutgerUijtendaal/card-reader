<template>
  <div
    class="card-decklist px-1 pb-3 pt-2"
    data-testid="card-decklist"
  >
    <section
      v-for="group in visibleGroups"
      :key="group.key"
      class="card-decklist-group"
      :class="{ 'card-decklist-group-flowing': !groupByType }"
      data-testid="card-decklist-group"
      :data-type-group-key="group.key"
    >
      <h3
        v-if="group.label"
        class="card-decklist-group-title"
      >
        <span>{{ group.label }}</span>
        <span class="tabular-nums">{{ countCards(group.entries) }}</span>
      </h3>
      <CardDecklistRow
        v-for="entry in group.entries"
        :key="entry.card.id"
        :card="entry.card"
        :quantity="entry.quantity"
        :hover-mode="hoverMode"
        :navigation-target="navigationTarget?.(entry.card.id)"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import CardDecklistRow from '@/domain/cards/components/CardDecklistRow.vue';
import type { CardListItem } from '@/domain/cards/types';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';

type Entry = { card: CardListItem; quantity: number };
type Group = { key: string; label: string; entries: Entry[] };

/**
 * A text decklist: one row per card with its quantity, name, and mana cost, flowing into as many
 * columns as the width allows. Hovering a row shows the card preview for the surface's hover mode.
 */
const props = defineProps<{
  entries: Entry[];
  groups: Group[];
  groupByType: boolean;
  hoverMode: HoverMode;
  navigationTarget?: (id: string) => RouteLocationRaw;
}>();

const visibleGroups = computed<Group[]>(() =>
  props.groupByType ? props.groups : [{ key: 'all', label: '', entries: props.entries }],
);

const countCards = (entries: Entry[]): number =>
  entries.reduce((sum, entry) => sum + entry.quantity, 0);
</script>

<style scoped>
/* Centered at a readable width like the About view; up to three columns. */
.card-decklist {
  max-width: 60rem;
  margin-inline: auto;
  columns: 17rem 3;
  column-gap: 2rem;
}

.card-decklist-group {
  break-inside: avoid;
  margin-bottom: 1.25rem;
}

/* An ungrouped list is one section, so it splits across the columns row by row. */
.card-decklist-group-flowing {
  break-inside: auto;
}

.card-decklist-group-flowing > :deep(*) {
  break-inside: avoid;
}

.card-decklist-group-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.25rem;
  padding: 0 0.5rem 0.375rem;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
</style>
