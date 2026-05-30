<template>
  <section class="space-y-3">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h3 class="theme-section-title text-xs font-semibold uppercase tracking-[0.16em]">
          {{ heading }}
        </h3>
        <p class="theme-section-muted mt-1 text-xs">
          {{ subheading }}
        </p>
      </div>
      <span class="theme-pill px-3 py-1 text-xs font-semibold uppercase tracking-wide">
        {{ deckReferences.length }} {{ deckReferences.length === 1 ? 'deck' : 'decks' }}
      </span>
    </div>

    <div
      v-if="deckReferences.length > 0"
      class="grid gap-3"
    >
      <div
        v-for="deck in deckReferences"
        :key="deck.id"
        class="space-y-2"
      >
        <DeckListCard
          :deck="deck"
          :mode="deck.owner.id === currentUserId ? 'owned' : 'browse'"
          :title-to="deckPath(deck)"
        />
        <div class="theme-muted flex flex-wrap items-center gap-x-3 gap-y-1 px-1 text-xs">
          <span v-if="deck.card_reference.is_hero">Includes as hero</span>
          <span v-if="deck.card_reference.mainboard_quantity > 0">Mainboard x{{ deck.card_reference.mainboard_quantity }}</span>
          <span v-if="deck.card_reference.sideboard_quantity > 0">Sideboard x{{ deck.card_reference.sideboard_quantity }}</span>
        </div>
      </div>
    </div>

    <div
      v-else
      class="relative"
    >
      <DeckLoadingSkeleton :animated="false" />
      <RouterLink
        class="absolute left-1/2 top-1/2 z-10 flex h-16 w-16 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border transition hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--theme-surface)]"
        style="border-color: color-mix(in srgb, var(--color-border-strong) 62%, transparent 38%); background: color-mix(in srgb, var(--color-surface-strong) 88%, transparent 12%); color: var(--color-text-muted);"
        aria-label="Create deck"
        title="Create deck"
        :to="createDeckLocation"
      >
        <Plus class="h-8 w-8" />
      </RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Plus } from 'lucide-vue-next';
import { computed } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import type { CardDeckReferenceSummary } from '@/modules/card-detail/types';
import { buildCardReturnContextLocation } from '@/modules/card-detail/cardReturnState';
import DeckLoadingSkeleton from '@/modules/decks/components/DeckLoadingSkeleton.vue';
import DeckListCard from '@/modules/decks/components/DeckListCard.vue';

const props = defineProps<{
  deckReferences: CardDeckReferenceSummary[];
  currentUserId?: string | null;
}>();

const route = useRoute();

const heading = computed(() => {
  const count = props.deckReferences.length;
  return `Card is in ${count} ${count === 1 ? 'deck' : 'decks'}`;
});

const subheading = computed(() =>
  props.deckReferences.length > 0
    ? 'Decks that include this card as a hero, mainboard card, or sideboard card.'
    : 'No visible deck currently includes this card.',
);
const createDeckLocation = computed(() =>
  buildCardReturnContextLocation('/my/decks/new', route.query, String(route.params.id)),
);

const deckPath = (deck: CardDeckReferenceSummary) =>
  buildCardReturnContextLocation(
    deck.owner.id === props.currentUserId ? `/my/decks/${deck.id}` : `/decks/${deck.id}`,
    route.query,
    String(route.params.id),
  );
</script>
