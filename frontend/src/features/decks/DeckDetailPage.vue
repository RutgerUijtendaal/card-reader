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
          :pending-suggestions="canEdit ? deck.pending_tag_suggestions ?? [] : []"
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

    <AppPageLayout
      columns="one"
      :root-class="detailsExpanded ? 'deck-detail-layout deck-detail-layout-expanded' : 'deck-detail-layout'"
    >
      <template #aside>
        <div
          class="deck-detail-aside-shell"
          :class="detailsExpanded ? 'deck-detail-aside-shell-expanded' : ''"
        >
          <AppStickyAside
            root-class="deck-detail-primary-aside"
            scroll-class="flex flex-col gap-5 space-y-0"
          >
            <div class="space-y-4">
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
                <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-sm">
                  <p
                    class="theme-section-muted"
                    data-testid="deck-owner"
                  >
                    By <span class="theme-section-title font-medium">{{ formatDeckOwnerName(deck.owner.username) }}</span>
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
                    <span class="deck-detail-header-action theme-section-muted inline-flex items-center gap-1 text-xs font-medium">
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

            <template #footer>
              <div class="flex flex-wrap items-center gap-3">
                <CardSortMenu
                  :sort="effectiveSort"
                  :default-sort="defaultSort"
                  :override-active="deckDetailSortOverride !== null"
                  allow-default-option
                  @update:sort="setDeckDetailSortOverride"
                  @reset="clearDeckDetailSortOverride"
                />
                <GalleryOptionsMenu
                  :hover-mode="effectiveHoverMode"
                  :default-hover-mode="defaultHoverMode"
                  :hover-mode-override-active="deckDetailHoverModeOverride !== null"
                  allow-hover-mode-default-option
                  :card-scale="cardScale"
                  :show-card-groups="false"
                  :show-card-groups-control="false"
                  :group-by-type="groupByType"
                  show-group-by-type-control
                  @update:hover-mode="setDeckDetailHoverModeOverride"
                  @reset:hover-mode="clearDeckDetailHoverModeOverride"
                  @update:card-scale="cardScale = $event"
                  @update:group-by-type="groupByType = $event"
                />
              </div>
            </template>
          </AppStickyAside>

          <Transition name="deck-detail-panel">
            <AppStickyAside
              v-if="detailsExpanded"
              id="deck-detail-panel"
              root-class="deck-detail-distribution-aside"
              scroll-class="space-y-5"
            >
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

              <template #footer>
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
            </AppStickyAside>
          </Transition>
        </div>
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

        <div
          v-if="!groupByType"
          class="grid gap-4 px-1 pb-3 pt-2"
          :style="mainboardGridStyle"
        >
          <CardGalleryItem
            v-for="entry in sortedActiveBoardEntries"
            :key="entry.card.id"
            class="justify-self-center"
            :style="mainboardCardStyle"
            :card="toGalleryCard(entry.card)"
            :card-height-rem="mainboardCardHeightRem"
            :hover-mode="effectiveHoverMode"
            :navigation-target="detailLocation(entry.card.id)"
          >
            <template #overlay>
              <div class="absolute inset-x-3 bottom-3 flex items-center justify-start gap-3">
                <DeckCardCountBadge :quantity="entry.quantity" />
              </div>
            </template>
          </CardGalleryItem>
        </div>
        <div
          v-else
          class="space-y-6 px-1 pb-3 pt-2"
        >
          <section
            v-for="group in groupedActiveBoardEntries"
            :key="group.key"
            class="space-y-3"
            data-testid="deck-type-group"
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
              :style="mainboardGridStyle"
            >
              <CardGalleryItem
                v-for="entry in group.entries"
                :key="entry.card.id"
                class="justify-self-center"
                :style="mainboardCardStyle"
                :card="toGalleryCard(entry.card)"
                :card-height-rem="mainboardCardHeightRem"
                :hover-mode="effectiveHoverMode"
                :navigation-target="detailLocation(entry.card.id)"
              >
                <template #overlay>
                  <div class="absolute inset-x-3 bottom-3 flex items-center justify-start gap-3">
                    <DeckCardCountBadge :quantity="entry.quantity" />
                  </div>
                </template>
              </CardGalleryItem>
            </div>
          </section>
        </div>
      </section>
    </AppPageLayout>
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
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';
import AppStickyAside from '@/shared/components/app/AppStickyAside.vue';
import CardGalleryItem from '@/domain/cards/components/CardGalleryItem.vue';
import CardMarkupText from '@/domain/cards/components/CardMarkupText.vue';
import { fetchCardFilters } from '@/domain/cards/api';
import CardSortMenu from '@/domain/cards/components/CardSortMenu.vue';
import GalleryOptionsMenu from '@/domain/cards/components/GalleryOptionsMenu.vue';
import DeckTagPills from '@/domain/decks/components/DeckTagPills.vue';
import TtsCopyIcon from '@/shared/components/icons/TtsCopyIcon.vue';
import { formatDeckOwnerName } from '@/domain/decks/utils/display';
import { deckDifficultyLabels } from '@/domain/decks/utils/difficulty';
import { useAuthStore } from '@/domain/session/store';
import { buildCardReturnLocation, isCardReturnQuery } from '@/domain/card-navigation/cardReturnState';
import {
  buildNotificationsReturnLocation,
  isNotificationsReturnQuery,
} from '@/domain/notifications/notificationRouteState';
import type { CardFiltersResponse, CardListItem } from '@/domain/cards/types';
import { buildTypeSortLookup, compareCardSort } from '@/domain/cards/utils/gallery/cardSort';
import { useCardSortSurface } from '@/domain/cards/composables/useCardSortPreferences';
import { useGalleryOptions } from '@/domain/cards/composables/useGalleryOptions';
import { useHoverModeSurface } from '@/domain/cards/composables/useHoverModePreferences';
import { fetchDeckDetail, fetchMyDeck } from '@/domain/decks/api';
import DeckCardCountBadge from '@/features/decks/components/DeckCardCountBadge.vue';
import DeckDetailLoadingSkeleton from '@/features/decks/components/DeckDetailLoadingSkeleton.vue';
import DeckManaDistribution from '@/features/decks/components/DeckManaDistribution.vue';
import DeckManaCurve from '@/features/decks/components/DeckManaCurve.vue';
import { buildDeckCardDetailLocation, buildDeckDetailEditorLocation } from '@/domain/decks/utils/deckRouteState';
import { groupDeckEntriesByType } from '@/domain/decks/utils/deckTypeGroups';
import { buildDeckShareUrl, canShareDeck } from '@/domain/decks/utils/share';
import type { DeckCardSummary, DeckEntrySummary, DeckRecord, DeckSideboardRecord } from '@/domain/decks/types';
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
const {
  defaultSort,
  overrideSort: deckDetailSortOverride,
  effectiveSort,
  setOverrideSort,
  clearOverrideSort,
} = useCardSortSurface('deckDetail');
const {
  defaultHoverMode,
  overrideHoverMode: deckDetailHoverModeOverride,
  effectiveHoverMode,
  setOverrideHoverMode,
  clearOverrideHoverMode,
} = useHoverModeSurface('deckDetail');
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

const canEdit = computed(() =>
  deck.value?.owner.id === auth.user?.id || auth.canAccessStaffRoutes,
);
const canShare = computed(() => (deck.value ? canShareDeck(deck.value) : false));
const difficultyLabel = computed(() => (
  deck.value?.difficulty ? deckDifficultyLabels[deck.value.difficulty] : null
));
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
const mainboardCardHeightRem = computed(() => Number((24 * cardScale.value).toFixed(2)));
const mainboardCardWidthRem = computed(() => Number(((mainboardCardHeightRem.value * 63) / 88).toFixed(2)));
const mainboardGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(${Math.round((mainboardCardWidthRem.value + 1) * 16)}px, 1fr))`,
}));
const mainboardCardStyle = computed(() => ({
  width: '100%',
  maxWidth: `${mainboardCardWidthRem.value}rem`,
}));
const activeSideboard = computed<DeckSideboardRecord | null>(
  () => deck.value?.sideboards.find((sideboard) => sideboard.id === activeBoardId.value) ?? null,
);
const activeBoardEntries = computed<DeckEntrySummary[]>(() => {
  if (!deck.value) {
    return [];
  }
  return activeBoardId.value === 'mainboard' ? deck.value.mainboard.entries : (activeSideboard.value?.entries ?? []);
});
const activeBoardTitle = computed(() =>
  activeBoardId.value === 'mainboard' ? 'Mainboard' : (activeSideboard.value?.name ?? 'Sideboard'),
);
const ttsExportButtonLabel = computed(() =>
  activeBoardId.value === 'mainboard' ? 'Copy Mainboard TTS' : 'Copy Sideboard TTS',
);
const activeBoardEmptyLabel = computed(() =>
  activeBoardId.value === 'mainboard' ? 'This deck does not have any mainboard cards yet.' : 'This sideboard does not have any cards yet.',
);
const typeSortLookup = computed(() => buildTypeSortLookup(filterOptions.value.types));
const sortedActiveBoardEntries = computed(() =>
  [...activeBoardEntries.value].sort((left, right) =>
    compareCardSort(left.card, right.card, effectiveSort.value, {
      cardPool: 'player',
      typeSortLookup: typeSortLookup.value,
    }),
  ),
);
const groupedActiveBoardEntries = computed(() =>
  groupDeckEntriesByType(activeBoardEntries.value, filterOptions.value.types, {
    compareEntries: effectiveSort.value === 'types_asc'
      ? undefined
      : (left, right) => compareCardSort(left.card, right.card, effectiveSort.value, {
          cardPool: 'player',
          typeSortLookup: typeSortLookup.value,
        }),
  }),
);
const detailLocation = (cardId: string) => buildDeckCardDetailLocation(cardId, String(route.params.id), route.query);

const setDeckDetailSortOverride = (value: typeof effectiveSort.value): void => {
  setOverrideSort(value);
};

const clearDeckDetailSortOverride = (): void => {
  clearOverrideSort();
};

const setDeckDetailHoverModeOverride = (value: typeof effectiveHoverMode.value): void => {
  setOverrideHoverMode(value);
};

const clearDeckDetailHoverModeOverride = (): void => {
  clearOverrideHoverMode();
};

const toGalleryCard = (card: DeckCardSummary): CardListItem => ({
  ...card,
  result_type: 'card',
});

const loadDeck = async (): Promise<void> => {
  deck.value = isOwnedRoute.value ? await fetchMyDeck(String(route.params.id)) : await fetchDeckDetail(String(route.params.id));
  activeBoardId.value = 'mainboard';
  activeDetailPanel.value = deck.value.long_description && canAutoExpandDetails.value ? 'summary' : null;
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
.deck-detail-aside-shell {
  min-width: 0;
}

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

.deck-detail-panel-enter-active,
.deck-detail-panel-leave-active {
  overflow: hidden;
  transition:
    max-height 240ms ease,
    opacity 180ms ease,
    transform 240ms ease;
}

.deck-detail-panel-enter-from,
.deck-detail-panel-leave-to {
  max-height: 0;
  opacity: 0;
  transform: translateY(-0.5rem);
}

.deck-detail-panel-enter-to,
.deck-detail-panel-leave-from {
  max-height: 100rem;
  opacity: 1;
  transform: translateY(0);
}

@media (min-width: 1280px) {
  :deep(.deck-detail-layout) {
    grid-template-columns: 22.5rem minmax(0, 1fr);
    transition: grid-template-columns 240ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  :deep(.deck-detail-layout-expanded) {
    grid-template-columns: 47.5rem minmax(0, 1fr);
  }

  .deck-detail-aside-shell {
    display: grid;
    grid-template-columns: 22.5rem 0;
    overflow: clip;
    transition: grid-template-columns 240ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  .deck-detail-aside-shell-expanded {
    grid-template-columns: 22.5rem 25rem;
  }

  :deep(.deck-detail-primary-aside) {
    z-index: 1;
  }

  :deep(.deck-detail-distribution-aside) {
    min-width: 0;
    overflow: hidden;
    border-right-width: 1px;
    border-left-width: 1px;
  }

  .deck-detail-panel-enter-active,
  .deck-detail-panel-leave-active {
    max-height: none;
    transition:
      opacity 180ms ease,
      transform 240ms ease;
  }

  .deck-detail-panel-enter-from,
  .deck-detail-panel-leave-to {
    max-height: none;
    transform: translateX(-0.75rem);
  }
}

@media (prefers-reduced-motion: reduce) {
  :deep(.deck-detail-layout),
  .deck-detail-aside-shell,
  .deck-detail-panel-enter-active,
  .deck-detail-panel-leave-active,
  .deck-detail-header-action,
  .deck-detail-panel-trigger,
  .deck-detail-header-action :deep(svg) {
    transition-duration: 0.01ms !important;
  }
}
</style>
