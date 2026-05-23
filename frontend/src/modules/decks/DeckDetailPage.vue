<template>
  <section
    v-if="deck"
    class="flex h-[calc(100vh-3rem)] min-h-0 flex-col gap-5 overflow-hidden"
  >
    <div class="page-card flex flex-col gap-4 lg:flex-row lg:justify-between">
      <div class="min-w-0">
        <h2 class="theme-section-title text-xl font-semibold">
          {{ deck.name }}
        </h2>
        <p class="theme-section-muted text-sm">
          By {{ deck.owner.username }}
        </p>
        <p
          v-if="deck.description"
          class="theme-section-title mt-3 text-sm"
        >
          {{ deck.description }}
        </p>
      </div>

      <div class="flex flex-wrap gap-2">
        <RouterLink
          class="btn-secondary"
          to="/decks"
        >
          Back to Decks
        </RouterLink>
        <RouterLink
          v-if="canEdit"
          class="btn-primary"
          :to="`/my/decks/${deck.id}/edit`"
        >
          Edit Deck
        </RouterLink>
      </div>
    </div>

    <div class="grid min-h-0 flex-1 gap-5 overflow-hidden xl:grid-cols-[360px_minmax(0,1fr)]">
      <div class="page-card flex min-h-0 flex-col">
        <div class="app-scrollbar flex-1 space-y-4 overflow-y-auto pr-1">
          <h3 class="theme-section-title text-base font-semibold">
            Hero
          </h3>
          <div class="space-y-3">
            <div class="theme-card-frame theme-card-image-well mx-auto aspect-[63/88] w-full max-w-[22rem] overflow-hidden rounded-2xl">
              <img
                v-if="deck.hero_card.image_url"
                :src="toAbsoluteApiUrl(deck.hero_card.image_url)"
                :alt="deck.hero_card.name"
                class="h-full w-full object-cover"
              >
              <div
                v-else
                class="theme-kicker flex h-full items-center justify-center text-xs"
              >
                No image
              </div>
            </div>

            <p class="theme-section-title text-lg font-semibold">
              {{ deck.hero_card.name }}
            </p>
          </div>
        </div>

        <div class="theme-divider mt-4 flex shrink-0 justify-start border-t pt-4">
          <GalleryOptionsMenu
            :tooltip-enabled="tooltipEnabled"
            :card-scale="cardScale"
            :show-card-groups="false"
            :show-card-groups-control="false"
            @update:tooltip-enabled="tooltipEnabled = $event"
            @update:card-scale="cardScale = $event"
          />
        </div>
      </div>

      <div class="page-card flex min-h-0 flex-col space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-3">
            <h3 class="theme-section-title text-base font-semibold">
              Mainboard
            </h3>
            <span class="theme-pill theme-pill-accent text-xs">
              {{ deck.mainboard.total_cards }} cards / {{ deck.mainboard.unique_cards }} unique
            </span>
          </div>
        </div>

        <div class="app-scrollbar min-h-0 flex-1 overflow-y-auto pr-1">
          <div
            class="grid gap-4 px-1 pb-3 pt-2"
            :style="mainboardGridStyle"
          >
            <CardGalleryItem
              v-for="entry in deck.mainboard.entries"
              :key="entry.card.id"
              class="justify-self-center"
              :style="mainboardCardStyle"
              :card="toGalleryCard(entry.card)"
              :card-height-rem="mainboardCardHeightRem"
              :tooltip-enabled="tooltipEnabled"
              :navigation-target="detailLocation(entry.card.id)"
            >
              <template #overlay>
                <div class="absolute inset-x-3 bottom-3 flex items-center justify-start gap-3">
                  <DeckCardCountBadge :quantity="entry.quantity" />
                </div>
              </template>
            </CardGalleryItem>
          </div>
        </div>
      </div>
    </div>
  </section>

  <div
    v-else
    class="page-card theme-section-muted text-sm"
  >
    Loading deck...
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { toAbsoluteApiUrl } from '@/api/client';
import CardGalleryItem from '@/components/cards/CardGalleryItem.vue';
import GalleryOptionsMenu from '@/components/cards/GalleryOptionsMenu.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import type { CardListItem } from '@/modules/card-detail/types';
import { useGalleryOptions } from '@/modules/card-search/useGalleryOptions';
import { fetchDeckDetail } from '@/modules/decks/api';
import DeckCardCountBadge from '@/modules/decks/components/DeckCardCountBadge.vue';
import { buildDeckCardDetailLocation } from '@/modules/decks/deckRouteState';
import type { DeckCardSummary, DeckRecord } from '@/modules/decks/types';

const route = useRoute();
const auth = useAuthStore();
const deck = ref<DeckRecord | null>(null);
const { tooltipEnabled, cardScale } = useGalleryOptions();

const canEdit = computed(() => deck.value?.owner.id === auth.user?.id);
const mainboardCardHeightRem = computed(() => Number((24 * cardScale.value).toFixed(2)));
const mainboardCardWidthRem = computed(() => Number(((mainboardCardHeightRem.value * 63) / 88).toFixed(2)));
const mainboardGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(${Math.round((mainboardCardWidthRem.value + 1) * 16)}px, 1fr))`,
}));
const mainboardCardStyle = computed(() => ({
  width: '100%',
  maxWidth: `${mainboardCardWidthRem.value}rem`,
}));
const detailLocation = (cardId: string) => buildDeckCardDetailLocation(cardId, String(route.params.id), route.query);

const toGalleryCard = (card: DeckCardSummary): CardListItem => ({
  ...card,
  result_type: 'card',
});

const loadDeck = async (): Promise<void> => {
  deck.value = await fetchDeckDetail(String(route.params.id));
};

onMounted(loadDeck);
</script>
