<template>
  <button
    class="deck-compact-card"
    :class="[
      mode === 'owned' ? 'deck-compact-card-owned' : 'deck-compact-card-browse',
      selected ? 'deck-compact-card-selected' : '',
    ]"
    type="button"
    :aria-pressed="selected"
    data-testid="deck-compact-card"
    @click="emit('select')"
    @keydown.enter.prevent="emit('select')"
    @keydown.space.prevent="emit('select')"
  >
    <span class="deck-compact-card-art">
      <img
        v-if="deck.hero_card.image_url"
        :src="toAbsoluteApiUrl(deck.hero_card.image_url)"
        :alt="deck.hero_card.name"
        class="deck-compact-card-art-image"
        draggable="false"
      >
      <span
        v-else
        class="deck-compact-card-art-fallback"
        aria-hidden="true"
      />
      <span
        class="deck-compact-card-art-overlay"
        aria-hidden="true"
      />
    </span>

    <span class="deck-compact-card-content">
      <span class="deck-compact-card-title-row">
        <span class="deck-compact-card-title">{{ deck.name }}</span>
        <span
          class="theme-pill shrink-0 text-xs"
          :class="titlePillClass"
        >
          {{ titlePillLabel }}
        </span>
        <span
          v-if="deprecatedCardCount > 0"
          class="theme-pill theme-pill-warning inline-flex shrink-0 items-center gap-1 px-2 py-1 text-xs"
          title="Deck contains deprecated cards"
        >
          <TriangleAlert class="h-3.5 w-3.5" />
          <span>{{ deprecatedCardCount }}</span>
        </span>
      </span>

      <span class="deck-compact-card-meta">
        Hero: {{ deck.hero_card.name }}
      </span>

      <span class="deck-compact-card-meta">
        {{ boardSummary }}
      </span>

      <span
        v-if="heroAffinitySymbols.length > 0"
        class="deck-compact-card-symbols"
      >
        <SymbolToken
          v-for="symbol in heroAffinitySymbols"
          :key="symbol.id"
          :asset-url="symbol.asset_url"
          :label="symbol.label"
          :text-token="symbol.text_token"
          class="h-5 w-5 p-0.5"
        />
      </span>
    </span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { TriangleAlert } from 'lucide-vue-next';
import { toAbsoluteApiUrl } from '@/api/client';
import SymbolToken from '@/components/SymbolToken.vue';
import { deckVisibilityBadgeClasses, deckVisibilityLabels } from '@/composables/decks/visibility';
import type { DeckListRecord } from '@/modules/decks/types';

const props = withDefaults(defineProps<{
  deck: DeckListRecord;
  mode: 'browse' | 'owned';
  selected?: boolean;
}>(), {
  selected: false,
});

const emit = defineEmits<{
  (e: 'select'): void;
}>();

const sideboardSummary = computed(() => {
  const sideboardCount = 'sideboard_count' in props.deck ? props.deck.sideboard_count : props.deck.sideboards.length;
  if (sideboardCount === 0) {
    return 'No sideboards';
  }
  return `${sideboardCount} sideboard${sideboardCount === 1 ? '' : 's'}`;
});
const boardSummary = computed(() =>
  `Maindeck ${props.deck.mainboard.total_cards} · ${props.deck.mainboard.unique_cards} unique · ${sideboardSummary.value}`,
);
const heroAffinitySymbols = computed(() =>
  props.deck.hero_card.symbols.filter((symbol) => symbol.symbol_type === 'affinity'),
);
const uppercaseFirstCharacter = (value: string): string =>
  value.length === 0 ? value : value[0].toLocaleUpperCase() + value.slice(1);
const ownerDisplayName = computed(() => uppercaseFirstCharacter(props.deck.owner.username));
const titlePillLabel = computed(() =>
  props.mode === 'owned' ? deckVisibilityLabels[props.deck.visibility] : ownerDisplayName.value,
);
const titlePillClass = computed(() =>
  props.mode === 'owned' ? deckVisibilityBadgeClasses[props.deck.visibility] : 'theme-pill-keyword',
);
const deprecatedCardCount = computed(() => props.deck.status.deprecated_card_count ?? 0);
</script>

<style scoped>
.deck-compact-card {
  --deck-compact-art-width: min(12.5rem, 45%);
  --deck-compact-art-mask: linear-gradient(90deg, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 0.96) 38%, rgba(0, 0, 0, 0.72) 56%, rgba(0, 0, 0, 0.24) 78%, transparent 100%);
  --deck-compact-art-position: 26% 12%;
  --deck-compact-content-padding-left: clamp(8.8rem, 39%, 12.75rem);
  position: relative;
  display: block;
  width: 100%;
  min-height: 7.25rem;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 0.7rem;
  background: color-mix(in srgb, var(--color-surface-strong) 78%, transparent);
  padding: 0;
  text-align: left;
  transition:
    border-color 150ms ease,
    background 150ms ease,
    transform 150ms ease,
    box-shadow 150ms ease;
}

.deck-compact-card:hover,
.deck-compact-card:focus-visible {
  border-color: color-mix(in srgb, var(--color-accent) 46%, var(--color-border));
  background: color-mix(in srgb, var(--color-surface-strong) 92%, transparent);
  outline: none;
  transform: translateY(-0.05rem);
}

.deck-compact-card-selected {
  border-color: color-mix(in srgb, var(--color-accent) 76%, var(--color-border));
  background: color-mix(in srgb, var(--color-accent) 16%, var(--color-surface-strong));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--color-accent) 48%, transparent);
}

.deck-compact-card-art {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--deck-compact-art-width);
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(148, 163, 184, 0.26), transparent 55%),
    linear-gradient(135deg, rgba(30, 41, 59, 0.96), rgba(15, 23, 42, 0.92));
  -webkit-mask-image: var(--deck-compact-art-mask);
  mask-image: var(--deck-compact-art-mask);
}

.deck-compact-card-art-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: var(--deck-compact-art-position);
  transform: scale(1.12);
  transition: transform 240ms ease;
}

.deck-compact-card:hover .deck-compact-card-art-image,
.deck-compact-card:focus-visible .deck-compact-card-art-image {
  transform: scale(1.18) translateX(0.12rem);
}

.deck-compact-card-art-fallback {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top left, rgba(244, 114, 182, 0.28), transparent 45%),
    radial-gradient(circle at bottom left, rgba(59, 130, 246, 0.22), transparent 48%),
    linear-gradient(140deg, rgba(30, 41, 59, 0.86), rgba(15, 23, 42, 0.94));
}

.deck-compact-card-art-overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(15, 23, 42, 0.06) 0%, rgba(15, 23, 42, 0.12) 40%, rgba(15, 23, 42, 0.24) 58%, rgba(15, 23, 42, 0.1) 76%, transparent 100%),
    linear-gradient(180deg, rgba(15, 23, 42, 0.08), rgba(15, 23, 42, 0.04));
  pointer-events: none;
}

.deck-compact-card-content {
  position: relative;
  z-index: 1;
  display: grid;
  min-width: 0;
  gap: 0.25rem;
  padding: 0.8rem 0.85rem 0.8rem var(--deck-compact-content-padding-left);
}

.deck-compact-card-title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.45rem;
}

.deck-compact-card-title {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  color: var(--color-text);
  font-size: 0.96rem;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.deck-compact-card-meta {
  overflow: hidden;
  color: var(--color-text-soft);
  font-size: 0.76rem;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.deck-compact-card-symbols {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  gap: 0.25rem;
  padding-top: 0.1rem;
}

@media (max-width: 640px) {
  .deck-compact-card {
    --deck-compact-art-width: min(9.5rem, 58%);
    --deck-compact-content-padding-left: clamp(7rem, 41%, 9.5rem);
  }
}
</style>
