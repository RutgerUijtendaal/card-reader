<template>
  <div
    v-if="!groupByType"
    class="grid gap-4 px-1 pb-3 pt-2"
    :style="gridStyle"
  >
    <CardGalleryItem
      v-for="entry in entries"
      :key="entry.card.id"
      class="justify-self-center"
      :style="cardStyle"
      :card="entry.card"
      :card-height-rem="cardHeightRem"
      :hover-mode="hoverMode"
      :navigation-target="navigationTarget?.(entry.card.id)"
    >
      <template #overlay>
        <div class="absolute inset-x-3 bottom-3 flex items-center justify-start gap-3">
          <CardCountBadge :quantity="entry.quantity" />
        </div>
      </template>
    </CardGalleryItem>
  </div>
  <div
    v-else
    class="space-y-6 px-1 pb-3 pt-2"
  >
    <section
      v-for="group in groups"
      :key="group.key"
      class="space-y-3"
      data-testid="card-type-group"
      :data-type-group-key="group.key"
    >
      <div class="flex items-center justify-between gap-3">
        <h3 class="theme-section-title text-sm font-semibold">
          {{ group.label }}
        </h3>
        <span class="theme-pill theme-pill-neutral text-xs">
          {{ group.entries.reduce((sum, entry) => sum + entry.quantity, 0) }} cards
        </span>
      </div>
      <div
        class="grid gap-4"
        :style="gridStyle"
      >
        <CardGalleryItem
          v-for="entry in group.entries"
          :key="entry.card.id"
          class="justify-self-center"
          :style="cardStyle"
          :card="entry.card"
          :card-height-rem="cardHeightRem"
          :hover-mode="hoverMode"
          :navigation-target="navigationTarget?.(entry.card.id)"
        >
          <template #overlay>
            <div class="absolute inset-x-3 bottom-3 flex items-center justify-start gap-3">
              <CardCountBadge :quantity="entry.quantity" />
            </div>
          </template>
        </CardGalleryItem>
      </div>
    </section>
  </div>
</template>
<script setup lang="ts">
import type { StyleValue } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import type { CardListItem } from '@/domain/cards/types';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';
import CardGalleryItem from '@/domain/cards/components/CardGalleryItem.vue';
import CardCountBadge from '@/domain/cards/components/CardCountBadge.vue';
type Entry = { card: CardListItem; quantity: number };
defineProps<{
  entries: Entry[];
  groups: Array<{ key: string; label: string; entries: Entry[] }>;
  groupByType: boolean;
  gridStyle: StyleValue;
  cardStyle: StyleValue;
  cardHeightRem: number;
  hoverMode: HoverMode;
  navigationTarget?: (id: string) => RouteLocationRaw;
}>();
</script>
