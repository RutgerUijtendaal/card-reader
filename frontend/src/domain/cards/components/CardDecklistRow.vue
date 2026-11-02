<template>
  <component
    :is="navigationTarget ? RouterLink : 'div'"
    ref="rowRef"
    :to="navigationTarget"
    class="card-decklist-row"
    data-testid="card-decklist-row"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
    @focusin="hovered = true"
    @focusout="hovered = false"
  >
    <span class="card-decklist-quantity tabular-nums">{{ quantity }}</span>
    <span class="min-w-0 flex-1 truncate">{{ card.name }}</span>
    <TriangleAlert
      v-if="cardIsDeprecated(card)"
      class="card-decklist-deprecated h-3.5 w-3.5 shrink-0"
      aria-label="Deprecated"
    />
    <span
      v-if="showManaCost"
      class="inline-flex shrink-0 items-center"
      data-testid="card-decklist-mana"
    >
      <SymbolizedText
        :tokens="card.mana_symbols"
        :text="card.mana_cost"
        :symbol-by-key="manaSymbolByKey"
      />
    </span>
  </component>
  <CardRowHoverPreview
    :anchor="rowElement"
    :card="card"
    :hover-mode="hoverMode"
    :active="hovered"
    placement="right-start"
  />
</template>

<script setup lang="ts">
import { computed, ref, type ComponentPublicInstance } from 'vue';
import { TriangleAlert } from 'lucide-vue-next';
import { RouterLink, type RouteLocationRaw } from 'vue-router';
import CardRowHoverPreview from '@/domain/cards/components/CardRowHoverPreview.vue';
import SymbolizedText from '@/domain/cards/components/SymbolizedText.vue';
import type { CardListItem } from '@/domain/cards/types';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';
import { cardIsDeprecated } from '@/domain/cards/utils/filters/cardLifecycle';

const props = defineProps<{
  card: CardListItem;
  quantity: number;
  hoverMode: HoverMode;
  navigationTarget?: RouteLocationRaw;
}>();

const hovered = ref(false);
const rowRef = ref<HTMLElement | ComponentPublicInstance | null>(null);
// RouterLink hands back a component instance; the preview anchors to its rendered element.
const rowElement = computed<HTMLElement | null>(() => {
  const row = rowRef.value;
  if (!row) {
    return null;
  }
  return row instanceof HTMLElement ? row : (row.$el as HTMLElement);
});
const manaSymbolByKey = computed(() =>
  Object.fromEntries(props.card.symbols.map((symbol) => [symbol.key, symbol])),
);
// Costless cards print 0 or a dash; the list leaves their cost column empty instead. This reads
// the printed cost, not mana_value, which counts variable costs such as X as zero.
const EMPTY_COST_TOKENS = new Set(['', '0', '-']);
const showManaCost = computed(() => {
  const symbols = props.card.mana_symbols.map((symbol) => symbol.trim());
  if (symbols.length > 0) {
    return symbols.some((symbol) => !EMPTY_COST_TOKENS.has(symbol));
  }
  return !EMPTY_COST_TOKENS.has(props.card.mana_cost.trim());
});
</script>

<style scoped>
.card-decklist-row {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  min-height: 2rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.375rem;
  color: var(--color-text);
  font-size: 0.875rem;
  transition: background-color 120ms ease;
}

.card-decklist-row:hover,
.card-decklist-row:focus-visible {
  background: color-mix(in srgb, var(--accent) 10%, transparent);
  outline: none;
}

.card-decklist-quantity {
  width: 1.25rem;
  flex-shrink: 0;
  text-align: right;
  font-weight: 600;
  color: var(--accent);
}

.card-decklist-deprecated {
  color: var(--color-pill-warning-text);
}
</style>
