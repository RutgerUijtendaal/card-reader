<template>
  <div class="deck-list-card-shell min-w-0">
    <div
      :class="cardClass"
      :data-navigation-target="navigationTarget"
      :role="isClickableCard ? 'link' : undefined"
      :tabindex="isClickableCard ? 0 : undefined"
      @click="handleCardClick"
      @keydown.enter.prevent="handleCardKeydown"
      @keydown.space.prevent="handleCardKeydown"
    >
      <div class="deck-list-card-art">
        <img
          v-if="deck.hero_card.image_url"
          :src="toAbsoluteApiUrl(deck.hero_card.image_url)"
          :alt="deck.hero_card.name"
          class="deck-list-card-art-image"
        >
        <div
          v-else
          class="deck-list-card-art-fallback"
          aria-hidden="true"
        />
      </div>

      <div class="deck-list-card-content">
        <div class="flex items-start gap-4">
          <div class="deck-list-card-main min-w-0 flex-1">
            <div class="deck-list-card-title-row flex min-w-0 items-center justify-between gap-3">
              <div class="flex min-w-0 flex-1 items-center gap-2">
                <h3 class="theme-section-title min-w-0 flex-1 truncate text-xl font-semibold">
                  {{ deck.name }}
                </h3>
                <span
                  v-if="deprecatedCardCount > 0"
                  class="theme-pill theme-pill-warning inline-flex shrink-0 items-center gap-1 px-2 py-1 text-xs"
                  title="Deck contains deprecated cards"
                >
                  <TriangleAlert class="h-3.5 w-3.5" />
                  <span>{{ deprecatedCardCount }}</span>
                </span>
              </div>
              <span
                class="deck-list-card-title-pill theme-pill shrink-0 text-xs"
                :class="titlePillClass"
              >
                {{ titlePillLabel }}
              </span>
            </div>

            <p
              v-if="deck.description"
              class="deck-list-card-description theme-section-title text-sm"
            >
              {{ deck.description }}
            </p>
            <p
              v-else
              class="deck-list-card-description theme-section-muted text-sm"
            >
              No description available.
            </p>
          </div>

          <div
            class="shrink-0"
            data-card-click-ignore="true"
          >
            <slot
              v-if="$slots.actions"
              name="actions"
            />

            <ExtraActionsMenu
              v-else-if="isBrowseMode"
              button-label="Open deck actions"
              panel-class="w-52"
            >
              <template #default="{ close }">
                <slot
                  name="menu-actions"
                  :close="close"
                />

                <button
                  class="btn-secondary app-menu-action"
                  type="button"
                  aria-label="Playtest deck"
                  @click="playtestDeck(close)"
                >
                  <Gamepad2
                    class="h-4 w-4 shrink-0"
                    aria-hidden="true"
                  />
                  Playtest
                </button>

                <button
                  v-if="canShareDeck(deck)"
                  class="btn-secondary app-menu-action"
                  type="button"
                  aria-label="Copy share link"
                  @click="copyShareLink(close)"
                >
                  <Share2
                    class="h-4 w-4 shrink-0"
                    aria-hidden="true"
                  />
                  Share
                </button>

                <button
                  class="btn-secondary app-menu-action"
                  type="button"
                  aria-label="Copy Mainboard TTS"
                  @click="exportDeck(close)"
                >
                  <TtsCopyIcon
                    class="h-4 w-4 shrink-0"
                    aria-hidden="true"
                  />
                  TTS
                </button>
              </template>
            </ExtraActionsMenu>
          </div>
        </div>

        <div class="deck-list-card-tags-region">
          <DeckTagPills
            class="deck-list-card-tags"
            :tags="deck.tags ?? []"
            :pending-suggestions="isOwnedMode ? deck.pending_tag_suggestions ?? [] : []"
            :max-visible="6"
          />
        </div>

        <div class="deck-list-card-footer flex flex-wrap items-center justify-between gap-3">
          <div class="deck-list-card-footer-meta theme-section-muted text-xs">
            <span class="deck-list-card-footer-meta-item">
              <LibraryBig
                class="h-4 w-4"
                aria-hidden="true"
              />
              <span>Maindeck {{ deck.mainboard.total_cards }}</span>
            </span>
            <span class="deck-list-card-footer-meta-item">
              <Copy
                class="h-4 w-4"
                aria-hidden="true"
              />
              <span>Unique {{ deck.mainboard.unique_cards }}</span>
            </span>
            <span class="deck-list-card-footer-meta-item">
              <PanelRight
                class="h-4 w-4"
                aria-hidden="true"
              />
              <span>Sideboards {{ sideboardCount }}</span>
            </span>
            <span
              v-if="difficultyLabel"
              class="deck-list-card-footer-meta-item"
              data-testid="deck-difficulty"
            >
              <Gauge
                class="h-4 w-4"
                aria-hidden="true"
              />
              <span>Difficulty · {{ difficultyLabel }}</span>
            </span>
            <span class="deck-list-card-footer-meta-item">
              <CalendarDays
                class="h-4 w-4"
                aria-hidden="true"
              />
              <span>Updated {{ formatDate(deck.updated_at) }}</span>
            </span>
          </div>

          <div
            v-if="heroAffinitySymbols.length > 0"
            class="flex flex-wrap items-center justify-end gap-1.5"
          >
            <SymbolToken
              v-for="symbol in heroAffinitySymbols"
              :key="symbol.id"
              :asset-url="symbol.asset_url"
              :label="symbol.label"
              :text-token="symbol.text_token"
              class="h-6 w-6 p-0.5"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { CalendarDays, Copy, Gamepad2, Gauge, LibraryBig, PanelRight, Share2, TriangleAlert } from 'lucide-vue-next';
import { useRouter, type RouteLocationRaw } from 'vue-router';
import { toast } from 'vue-sonner';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import SymbolToken from '@/domain/cards/components/SymbolToken.vue';
import ExtraActionsMenu from '@/shared/components/app/ExtraActionsMenu.vue';
import DeckTagPills from '@/domain/decks/components/DeckTagPills.vue';
import TtsCopyIcon from '@/shared/components/icons/TtsCopyIcon.vue';
import { formatDeckOwnerName } from '@/domain/decks/utils/display';
import { deckDifficultyLabels } from '@/domain/decks/utils/difficulty';
import { buildDeckShareUrl, canShareDeck } from '@/domain/decks/utils/share';
import type { DeckListRecord } from '@/domain/decks/types';
import { useDeckExport } from '@/domain/decks/composables/useDeckExport';
import { deckVisibilityBadgeClasses, deckVisibilityLabels } from '@/domain/decks/utils/visibility';

const props = defineProps<{
  deck: DeckListRecord;
  mode: 'browse' | 'owned';
  titleTo?: RouteLocationRaw;
}>();

const router = useRouter();
const { exportTtsDeck } = useDeckExport();

const isBrowseMode = computed(() => props.mode === 'browse');
const isOwnedMode = computed(() => props.mode === 'owned');
const isClickableCard = computed(() => Boolean(props.titleTo));
const navigationTarget = computed(() =>
  props.titleTo ? router.resolve(props.titleTo).fullPath : undefined,
);
const formatDate = (value: string): string => {
  const date = new Date(value);
  return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()}`;
};
const sideboardCount = computed(() =>
  'sideboard_count' in props.deck ? props.deck.sideboard_count : props.deck.sideboards.length,
);
const heroAffinitySymbols = computed(() => props.deck.hero_card.symbols.filter((symbol) => symbol.symbol_type === 'affinity'));
const ownerDisplayName = computed(() => formatDeckOwnerName(props.deck.owner.username));
const titlePillLabel = computed(() => (isOwnedMode.value ? deckVisibilityLabels[props.deck.visibility] : ownerDisplayName.value));
const titlePillClass = computed(() => (isOwnedMode.value ? deckVisibilityBadgeClasses[props.deck.visibility] : 'theme-pill-neutral'));
const deprecatedCardCount = computed(() => props.deck.status.deprecated_card_count ?? 0);
const difficultyLabel = computed(() => (
  props.deck.difficulty ? deckDifficultyLabels[props.deck.difficulty] : null
));
const cardClass = computed(() => [
  'deck-list-card-surface',
  'page-card',
  isBrowseMode.value ? 'deck-list-card-browse' : 'deck-list-card-owned',
  isClickableCard.value
    ? 'cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--theme-surface)]'
    : '',
]);

const interactiveSelector =
  'a, button, input, select, textarea, summary, details, [role="button"], [data-card-click-ignore="true"]';

const shouldIgnoreCardNavigation = (target: EventTarget | null): boolean => {
  if (!(target instanceof Element)) {
    return false;
  }
  return target.closest(interactiveSelector) !== null;
};

const navigateToCard = (): void => {
  if (!props.titleTo) {
    return;
  }
  void router.push(props.titleTo);
};

const copyShareLink = async (close: () => void): Promise<void> => {
  if (!canShareDeck(props.deck)) {
    return;
  }
  await navigator.clipboard.writeText(buildDeckShareUrl(props.deck.id));
  toast.success('Share link copied.');
  close();
};

const playtestDeck = (close: () => void): void => {
  void router.push(`/playtester/${props.deck.id}`);
  close();
};

const exportDeck = async (close: () => void): Promise<void> => {
  await exportTtsDeck(props.deck.id);
  close();
};

const handleCardClick = (event: MouseEvent): void => {
  if (!isClickableCard.value || shouldIgnoreCardNavigation(event.target)) {
    return;
  }
  navigateToCard();
};

const handleCardKeydown = (event: KeyboardEvent): void => {
  if (!isClickableCard.value || shouldIgnoreCardNavigation(event.target)) {
    return;
  }
  navigateToCard();
};
</script>

<style scoped>
.deck-list-card-surface {
  --deck-card-art-text-gap: 1.5rem;
  --deck-card-art-position: 23% 7%;
  --deck-card-art-scale: 1.265;
  --deck-card-art-hover-scale: 1.27;
  --deck-card-art-hover-shift-x: 0.2rem;
  --deck-card-content-padding-left: 20rem;
  --deck-card-art-width: calc(var(--deck-card-content-padding-left) - var(--deck-card-art-text-gap));
  position: relative;
  min-height: 14.5rem;
  overflow: hidden;
  padding: 0;
}

.deck-list-card-art {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--deck-card-art-width);
  overflow: hidden;
  border: 1px solid var(--color-border-strong);
  border-radius: 0.75rem 0 0 0.75rem;
  background:
    radial-gradient(circle at top left, rgba(148, 163, 184, 0.26), transparent 55%),
    linear-gradient(135deg, rgba(30, 41, 59, 0.96), rgba(15, 23, 42, 0.92));
}

.deck-list-card-art-image {
  height: 100%;
  width: 100%;
  object-fit: cover;
  object-position: var(--deck-card-art-position);
  transform: scale(var(--deck-card-art-scale));
  transition: transform 240ms ease;
}

.deck-list-card-surface:hover .deck-list-card-art-image,
.deck-list-card-surface:focus-within .deck-list-card-art-image {
  transform: scale(var(--deck-card-art-hover-scale)) translateX(var(--deck-card-art-hover-shift-x));
}

.deck-list-card-art-fallback {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top left, rgba(244, 114, 182, 0.32), transparent 45%),
    radial-gradient(circle at bottom left, rgba(59, 130, 246, 0.24), transparent 48%),
    linear-gradient(140deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.96));
}

.deck-list-card-content {
  position: relative;
  z-index: 1;
  display: flex;
  min-height: inherit;
  min-width: 0;
  flex-direction: column;
  padding: 1.1rem 1.2rem 1.1rem var(--deck-card-content-padding-left);
}

.deck-list-card-description {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 0.75rem;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.deck-list-card-main {
  display: flex;
  flex-direction: column;
}

.deck-list-card-tags-region {
  display: flex;
  flex: 1;
  align-items: center;
  padding-block: 0.75rem;
}

.deck-list-card-tags {
  align-items: center;
}

.deck-list-card-footer-meta {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  align-items: center;
  row-gap: 0.35rem;
}

.deck-list-card-footer-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  white-space: nowrap;
}

.deck-list-card-footer-meta-item + .deck-list-card-footer-meta-item {
  margin-left: 0.75rem;
  border-left: 1px solid var(--color-border-strong);
  padding-left: 0.75rem;
}

@media (max-width: 767px) {
  .deck-list-card-surface {
    --deck-card-art-text-gap: 1rem;
    --deck-card-content-padding-left: clamp(5.4rem, 24%, 7.5rem);
    min-height: 12rem;
  }

  .deck-list-card-content {
    padding: 0.95rem 1rem 0.95rem var(--deck-card-content-padding-left);
  }
}
</style>
