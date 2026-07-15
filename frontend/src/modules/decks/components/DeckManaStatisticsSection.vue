<template>
  <section
    class="space-y-3"
    data-testid="mana-statistics-section"
  >
    <div class="flex items-center justify-between gap-3">
      <h4 class="theme-section-title text-sm font-semibold">
        {{ title }}
      </h4>
      <span class="theme-pill theme-pill-neutral text-[10px]">
        {{ totalCards }} {{ totalCards === 1 ? 'card' : 'cards' }}
      </span>
    </div>
    <div class="mana-statistics-grid text-xs">
      <span class="theme-kicker">Color</span>
      <span class="theme-kicker text-right">Total</span>
      <span class="theme-kicker text-right">Average</span>
      <span class="theme-kicker text-right">Highest</span>

      <template
        v-for="color in colors"
        :key="color.key"
      >
        <div class="theme-section-title flex min-w-0 items-center gap-2 py-1.5">
          <SymbolToken
            :asset-url="color.assetUrl"
            :label="color.label"
            :text-token="color.textToken"
            class="h-5 w-5 shrink-0 text-[9px] font-semibold"
          />
          <span
            class="truncate font-medium"
            :title="color.label"
          >
            {{ color.label }}
          </span>
        </div>
        <span class="theme-section-title py-1.5 text-right font-semibold tabular-nums">
          {{ color.total }}
        </span>
        <span class="theme-section-muted py-1.5 text-right tabular-nums">
          {{ formatAverage(color.average) }}
        </span>
        <span class="theme-section-muted py-1.5 text-right tabular-nums">
          {{ color.highest }}
        </span>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import SymbolToken from '@/components/SymbolToken.vue';
import type { ManaColorStatistics } from '@/composables/decks/manaDistribution';

defineProps<{
  title: string;
  totalCards: number;
  colors: ManaColorStatistics[];
}>();

const formatAverage = (value: number): string => value.toFixed(2);
</script>

<style scoped>
.mana-statistics-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) repeat(3, minmax(3.25rem, auto));
  column-gap: 0.75rem;
  align-items: center;
}

.mana-statistics-grid > :nth-child(n + 5) {
  border-top: 1px solid color-mix(in srgb, var(--color-border) 54%, transparent 46%);
}
</style>
