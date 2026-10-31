<template>
  <DeckDetailLoadingSkeleton
    v-if="loadingInitial"
    :back-to="backLink"
    :back-label="backLabel"
    :grid-style="mainboardGridStyle"
    :card-style="mainboardCardStyle"
    :group-by-type="groupByType"
  />

  <section
    v-else-if="deck"
    class="flex flex-col gap-5"
  >
    <AppPageHeader
      :icon="BookOpenText"
      :title="deck.name"
      :back-to="backLink"
      :back-label="backLabel"
      title-tag="h2"
      title-class="text-xl"
      subtitle-class="!mt-4 text-sm"
    >
      <template #subtitle>
        <DeckTagPills
          :tags="deck.tags ?? []"
          :pending-suggestions="canEdit ? (deck.pending_tag_suggestions ?? []) : []"
        />
      </template>

      <template #actions>
        <AppHeaderAction
          v-if="canEdit && canShare"
          :icon="Share2"
          label="Copy share link"
          short-label="Share"
          @click="copyShareLink"
        />
        <AppHeaderAction
          :icon="TtsCopyIcon"
          :label="ttsExportButtonLabel"
          short-label="TTS"
          @click="handleTtsExport"
        />
        <AppHeaderAction
          v-if="canEdit"
          :icon="Pencil"
          label="Edit deck"
          short-label="Edit"
          :to="buildDeckDetailEditorLocation(deck.id)"
        />
        <AppHeaderAction
          :icon="Gamepad2"
          label="Playtest deck"
          short-label="Playtest"
          variant="primary"
          :to="`/playtester/${deck.id}`"
        />
      </template>
    </AppPageHeader>

    <CollectionDetailLayout
      :expanded="detailsExpanded"
      details-id="deck-detail-panel"
    >
      <template #aside>
        <div class="space-y-4">
          <h3 class="theme-section-title text-base font-semibold">
            Hero
          </h3>
          <div class="space-y-3">
            <div
              class="theme-card-frame theme-card-image-well mx-auto aspect-[63/88] w-full max-w-[22rem] overflow-hidden rounded-2xl"
            >
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
            <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-sm">
              <p
                class="theme-section-muted"
                data-testid="deck-owner"
              >
                By
                <span class="theme-section-title font-medium">{{
                  formatDeckOwnerName(deck.owner.username)
                }}</span>
              </p>
              <p
                v-if="difficultyLabel"
                class="theme-section-muted flex shrink-0 items-center gap-1.5"
                data-testid="deck-difficulty"
              >
                <Gauge
                  class="h-4 w-4"
                  aria-hidden="true"
                />
                <span>Difficulty · {{ difficultyLabel }}</span>
              </p>
            </div>
          </div>

          <section
            class="theme-divider space-y-2 border-t pt-4"
            :class="deck.long_description ? 'deck-detail-panel-trigger' : ''"
            :role="deck.long_description ? 'button' : undefined"
            :tabindex="deck.long_description ? 0 : undefined"
            :aria-expanded="deck.long_description ? activeDetailPanel === 'summary' : undefined"
            :aria-controls="deck.long_description ? 'deck-detail-panel' : undefined"
            data-testid="deck-description"
            @click="deck.long_description && toggleDetailPanel('summary')"
            @keydown.enter="deck.long_description && toggleDetailPanel('summary')"
            @keydown.space.prevent="deck.long_description && toggleDetailPanel('summary')"
          >
            <div class="flex items-center justify-between gap-3">
              <h4 class="theme-section-title text-sm font-semibold">
                Summary
              </h4>
              <span
                v-if="deck.long_description"
                class="deck-detail-header-action theme-section-muted inline-flex items-center gap-1 text-xs font-medium"
                data-testid="deck-summary-details-button"
              >
                <span>Details</span>
                <ChevronRight
                  class="h-3.5 w-3.5 transition-transform duration-200"
                  :class="activeDetailPanel === 'summary' ? 'rotate-90' : ''"
                  aria-hidden="true"
                />
              </span>
            </div>
            <CardMarkupText
              v-if="deck.description_markup || deck.description"
              class="theme-section-muted text-sm"
              :markup="deck.description_markup || deck.description || ''"
              :hover-mode="effectiveHoverMode"
            />
            <p
              v-else
              class="theme-section-muted text-sm leading-6"
            >
              No description provided.
            </p>
          </section>
        </div>

        <div
          class="!mt-auto space-y-3"
          data-testid="deck-mana-section"
        >
          <div
            class="deck-detail-panel-trigger"
            role="button"
            tabindex="0"
            :aria-expanded="activeDetailPanel === 'mana'"
            aria-controls="deck-detail-panel"
            data-testid="deck-mana-details-button"
            @click="toggleDetailPanel('mana')"
            @keydown.enter="toggleDetailPanel('mana')"
            @keydown.space.prevent="toggleDetailPanel('mana')"
          >
            <DeckManaCurve
              :entries="activeBoardEntries"
              :empty-label="activeBoardEmptyLabel"
            >
              <template #header-actions>
                <span
                  class="deck-detail-header-action theme-section-muted inline-flex items-center gap-1 text-xs font-medium"
                >
                  <span>Details</span>
                  <ChevronRight
                    class="h-3.5 w-3.5 transition-transform duration-200"
                    :class="activeDetailPanel === 'mana' ? 'rotate-90' : ''"
                    aria-hidden="true"
                  />
                </span>
              </template>
            </DeckManaCurve>
          </div>
        </div>
      </template>
      <template #aside-footer>
        <CardCollectionViewOptions
          v-model:card-scale="cardScale"
          v-model:group-by-type="groupByType"
          :sort-surface="sortSurface"
          :hover-surface="hoverSurface"
        />
      </template>
      <template #details>
        <section
          v-if="activeDetailPanel === 'summary' && deck.long_description"
          class="space-y-2"
          data-testid="deck-long-description"
        >
          <h3 class="theme-section-title text-base font-semibold">
            About this deck
          </h3>
          <CardMarkupText
            class="theme-section-muted break-words text-sm"
            :markup="deck.long_description_markup || deck.long_description"
            :hover-mode="effectiveHoverMode"
          />
        </section>
        <DeckManaDistribution
          v-else-if="activeDetailPanel === 'mana'"
          :entries="activeBoardEntries"
          :symbols="filterOptions.symbols"
          :types="filterOptions.types"
        />
      </template>
      <template #details-footer>
        <button
          class="theme-ghost-button flex w-full items-center justify-center gap-2 px-3 py-2 text-sm font-semibold"
          type="button"
          data-testid="deck-detail-close-button"
          @click="closeDetailPanel"
        >
          <X
            class="h-4 w-4"
            aria-hidden="true"
          />
          Close details
        </button>
      </template>
      <section class="space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-2">
            <button
              class="theme-pill text-xs"
              :class="activeBoardId === 'mainboard' ? 'theme-pill-accent' : 'theme-pill-neutral'"
              type="button"
              @click="activeBoardId = 'mainboard'"
            >
              Mainboard
              <span class="ml-1 opacity-80">
                {{ deck.mainboard.total_cards }} / {{ deck.mainboard.unique_cards }}
              </span>
            </button>
            <button
              v-for="sideboard in deck.sideboards"
              :key="sideboard.id"
              class="theme-pill text-xs"
              :class="activeBoardId === sideboard.id ? 'theme-pill-accent' : 'theme-pill-neutral'"
              type="button"
              @click="activeBoardId = sideboard.id"
            >
              {{ sideboard.name }}
              <span class="ml-1 opacity-80">
                {{ sideboard.total_cards }} / {{ sideboard.unique_cards }}
              </span>
            </button>
          </div>

          <span class="theme-pill theme-pill-neutral shrink-0 text-xs">
            {{ deck.totals.overall_total_cards }} total across all boards
          </span>
        </div>

        <div class="sr-only">
          <h3>
            {{ activeBoardTitle }}
          </h3>
        </div>

        <CardCollectionGrid
          :entries="sortedActiveBoardEntries"
          :groups="groupedActiveBoardEntries"
          :group-by-type="groupByType"
          :grid-style="mainboardGridStyle"
          :card-style="mainboardCardStyle"
          :card-height-rem="mainboardCardHeightRem"
          :hover-mode="effectiveHoverMode"
          :navigation-target="detailLocation"
        />
      </section>
    </CollectionDetailLayout>
  </section>

  <div
    v-else
    class="page-card theme-section-muted text-sm"
  >
    Deck not found.
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useLocalStorage, useMediaQuery } from '@vueuse/core';
import { BookOpenText, ChevronRight, Gamepad2, Gauge, Pencil, Share2, X } from 'lucide-vue-next';
import { useRoute } from 'vue-router';
import { toast } from 'vue-sonner';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import CollectionDetailLayout from '@/shared/components/CollectionDetailLayout.vue';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';
import CardCollectionGrid from '@/domain/cards/components/CardCollectionGrid.vue';
import CardMarkupText from '@/domain/cards/components/CardMarkupText.vue';
import { fetchCardFilters } from '@/domain/cards/api';
import CardCollectionViewOptions from '@/domain/cards/components/CardCollectionViewOptions.vue';
import DeckTagPills from '@/domain/decks/components/DeckTagPills.vue';
import TtsCopyIcon from '@/shared/components/icons/TtsCopyIcon.vue';
import { formatDeckOwnerName } from '@/domain/decks/utils/display';
import { deckDifficultyLabels } from '@/domain/decks/utils/difficulty';
import { useAuthStore } from '@/domain/session/store';
import {
  buildCardReturnLocation,
  isCardReturnQuery,
} from '@/domain/card-navigation/cardReturnState';
import {
  buildNotificationsReturnLocation,
  isNotificationsReturnQuery,
} from '@/domain/notifications/notificationRouteState';
import type { CardFiltersResponse, CardListItem } from '@/domain/cards/types';
import { useCardCollectionGrid } from '@/domain/cards/composables/useCardCollectionGrid';
import { useCardSortSurface } from '@/domain/cards/composables/useCardSortPreferences';
import { useGalleryOptions } from '@/domain/cards/composables/useGalleryOptions';
import { useHoverModeSurface } from '@/domain/cards/composables/useHoverModePreferences';
import { fetchDeckDetail, fetchMyDeck } from '@/domain/decks/api';
import DeckDetailLoadingSkeleton from '@/domain/cards/components/CardCollectionDetailLoadingSkeleton.vue';
import DeckManaDistribution from '@/features/decks/components/DeckManaDistribution.vue';
import DeckManaCurve from '@/features/decks/components/DeckManaCurve.vue';
import {
  buildDeckCardDetailLocation,
  buildDeckDetailEditorLocation,
} from '@/domain/decks/utils/deckRouteState';
import { buildDeckShareUrl, canShareDeck } from '@/domain/decks/utils/share';
import type {
  DeckCardSummary,
  DeckEntrySummary,
  DeckRecord,
  DeckSideboardRecord,
} from '@/domain/decks/types';
import { useDeckExport } from '@/domain/decks/composables/useDeckExport';

const route = useRoute();
const auth = useAuthStore();
const deck = ref<DeckRecord | null>(null);
const loadingInitial = ref(true);
const filterOptions = ref<CardFiltersResponse>({
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
});
const { cardScale } = useGalleryOptions();
const sortSurface = useCardSortSurface('deckDetail');
const { effectiveSort } = sortSurface;
const hoverSurface = useHoverModeSurface('deckDetail');
const { effectiveHoverMode } = hoverSurface;
const { exportTtsDeck } = useDeckExport();
const activeBoardId = ref('mainboard');
type DeckDetailPanel = 'summary' | 'mana';
const activeDetailPanel = ref<DeckDetailPanel | null>(null);
const detailsExpanded = computed(() => activeDetailPanel.value !== null);
const canAutoExpandDetails = useMediaQuery('(min-width: 1536px)');
const toggleDetailPanel = (panel: DeckDetailPanel): void => {
  activeDetailPanel.value = activeDetailPanel.value === panel ? null : panel;
};
const closeDetailPanel = (): void => {
  activeDetailPanel.value = null;
};
const groupByType = useLocalStorage('card-reader.deck-detail-group-by-type', true, {
  writeDefaults: true,
});
const isOwnedRoute = computed(() => route.path.startsWith('/my/decks/'));

const canEdit = computed(() => deck.value?.owner.id === auth.user?.id || auth.canAccessStaffRoutes);
const canShare = computed(() => (deck.value ? canShareDeck(deck.value) : false));
const difficultyLabel = computed(() =>
  deck.value?.difficulty ? deckDifficultyLabels[deck.value.difficulty] : null,
);
const backLink = computed(() => {
  if (isNotificationsReturnQuery(route.query)) {
    return buildNotificationsReturnLocation();
  }
  if (isCardReturnQuery(route.query)) {
    return buildCardReturnLocation(route.query);
  }
  return isOwnedRoute.value ? '/my/decks' : '/decks';
});
const backLabel = computed(() => {
  if (isNotificationsReturnQuery(route.query)) {
    return 'Back to Notifications';
  }
  if (isCardReturnQuery(route.query)) {
    return 'Back to Card';
  }
  return isOwnedRoute.value ? 'Back to My Decks' : 'Back to Decks';
});
const activeSideboard = computed<DeckSideboardRecord | null>(
  () => deck.value?.sideboards.find((sideboard) => sideboard.id === activeBoardId.value) ?? null,
);
const activeBoardEntries = computed<DeckEntrySummary[]>(() => {
  if (!deck.value) {
    return [];
  }
  return activeBoardId.value === 'mainboard'
    ? deck.value.mainboard.entries
    : (activeSideboard.value?.entries ?? []);
});
const activeBoardTitle = computed(() =>
  activeBoardId.value === 'mainboard' ? 'Mainboard' : (activeSideboard.value?.name ?? 'Sideboard'),
);
const ttsExportButtonLabel = computed(() =>
  activeBoardId.value === 'mainboard' ? 'Copy Mainboard TTS' : 'Copy Sideboard TTS',
);
const activeBoardEmptyLabel = computed(() =>
  activeBoardId.value === 'mainboard'
    ? 'This deck does not have any mainboard cards yet.'
    : 'This sideboard does not have any cards yet.',
);
const {
  cardHeightRem: mainboardCardHeightRem,
  gridStyle: mainboardGridStyle,
  cardStyle: mainboardCardStyle,
  sortedEntries: sortedActiveBoardEntries,
  groupedEntries: groupedActiveBoardEntries,
} = useCardCollectionGrid(
  computed(() =>
    activeBoardEntries.value.map((entry) => ({ ...entry, card: toGalleryCard(entry.card) })),
  ),
  computed(() => filterOptions.value.types),
  'player',
  effectiveSort,
  cardScale,
);
const detailLocation = (cardId: string) =>
  buildDeckCardDetailLocation(cardId, String(route.params.id), route.query);

const toGalleryCard = (card: DeckCardSummary): CardListItem => ({
  ...card,
  result_type: 'card',
});

const loadDeck = async (): Promise<void> => {
  deck.value = isOwnedRoute.value
    ? await fetchMyDeck(String(route.params.id))
    : await fetchDeckDetail(String(route.params.id));
  activeBoardId.value = 'mainboard';
  activeDetailPanel.value =
    deck.value.long_description && canAutoExpandDetails.value ? 'summary' : null;
};

const loadFilterOptions = async (): Promise<void> => {
  filterOptions.value = await fetchCardFilters('player');
};

const handleTtsExport = async (): Promise<void> => {
  if (!deck.value) {
    return;
  }
  if (activeSideboard.value) {
    await exportTtsDeck(deck.value.id, {
      sideboardId: activeSideboard.value.id,
      successMessage: 'TTS sideboard copied to clipboard',
    });
    return;
  }
  await exportTtsDeck(deck.value.id, {
    successMessage: 'TTS mainboard copied to clipboard',
  });
};

const copyShareLink = async (): Promise<void> => {
  if (!deck.value || !canShare.value) {
    return;
  }
  await navigator.clipboard.writeText(buildDeckShareUrl(deck.value.id));
  toast.success('Share link copied.');
};

onMounted(async () => {
  try {
    await Promise.all([loadDeck(), loadFilterOptions()]);
  } finally {
    loadingInitial.value = false;
  }
});
</script>

<style scoped>
.deck-detail-header-action {
  overflow: clip;
  transition: color 180ms ease;
}

.deck-detail-header-action:hover {
  color: var(--color-text);
}

.deck-detail-panel-trigger {
  cursor: pointer;
  outline: none;
  transition:
    background-color 180ms ease,
    color 180ms ease;
}

.deck-detail-panel-trigger:hover {
  background: color-mix(in srgb, var(--theme-accent) 7%, transparent);
}

.deck-detail-panel-trigger:focus-visible {
  box-shadow: 0 0 0 2px var(--theme-accent);
}
</style>
