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
        <div
          class="deck-list-card-art-overlay"
          aria-hidden="true"
        />
      </div>

      <div class="deck-list-card-content">
        <div class="flex items-start gap-4">
          <div class="min-w-0 flex-1 space-y-3">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="theme-section-title truncate text-lg font-semibold">
                {{ deck.name }}
              </h3>
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
            </div>

            <p class="theme-section-muted text-sm">
              Hero: {{ deck.hero_card.name }}
            </p>

            <p class="theme-section-muted text-sm">
              {{ boardSummary }}
            </p>

            <p
              v-if="deck.description && !isCompact"
              class="deck-list-card-description theme-section-title text-sm"
            >
              {{ deck.description }}
            </p>
            <p
              v-else-if="!isCompact"
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
              v-if="isOwnedMode && $slots.actions"
              name="actions"
            />

            <ExtraActionsMenu
              v-else-if="isBrowseMode"
              button-label="Open deck actions"
            >
              <template #default="{ close }">
                <button
                  v-if="canShareDeck(deck)"
                  class="btn-secondary w-full justify-center"
                  type="button"
                  @click="copyShareLink(close)"
                >
                  Copy Share Link
                </button>

                <button
                  class="btn-secondary w-full justify-center"
                  type="button"
                  @click="exportDeck(close)"
                >
                  Export TTS
                </button>
              </template>
            </ExtraActionsMenu>
          </div>
        </div>

        <div class="mt-auto flex items-end justify-between gap-3 pt-3">
          <p class="theme-section-muted text-xs">
            Updated {{ formatDate(deck.updated_at) }}
          </p>

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
import { TriangleAlert } from 'lucide-vue-next';
import { useRouter, type RouteLocationRaw } from 'vue-router';
import { toast } from 'vue-sonner';
import { toAbsoluteApiUrl } from '@/api/client';
import SymbolToken from '@/components/SymbolToken.vue';
import ExtraActionsMenu from '@/components/app/ExtraActionsMenu.vue';
import { buildDeckShareUrl, canShareDeck } from '@/composables/decks/share';
import type { DeckRecord } from '@/modules/decks/types';
import { useDeckExport } from '@/composables/useDeckExport';
import { deckVisibilityBadgeClasses, deckVisibilityLabels } from '@/composables/decks/visibility';

const props = defineProps<{
  deck: DeckRecord;
  mode: 'browse' | 'owned';
  titleTo?: RouteLocationRaw;
  density?: 'default' | 'compact';
}>();

const router = useRouter();
const { exportTtsDeck } = useDeckExport();

const isBrowseMode = computed(() => props.mode === 'browse');
const isOwnedMode = computed(() => props.mode === 'owned');
const isCompact = computed(() => props.density === 'compact');
const isClickableCard = computed(() => Boolean(props.titleTo));
const navigationTarget = computed(() =>
  props.titleTo ? router.resolve(props.titleTo).fullPath : undefined,
);
const formatDate = (value: string): string => new Date(value).toLocaleDateString();
const sideboardSummary = computed(() => {
  if (props.deck.sideboards.length === 0) {
    return 'No sideboards';
  }
  return `${props.deck.sideboards.length} sideboard${props.deck.sideboards.length === 1 ? '' : 's'}`;
});
const boardSummary = computed(() => `Maindeck ${props.deck.mainboard.total_cards} · ${props.deck.mainboard.unique_cards} unique · ${sideboardSummary.value}`);
const heroAffinitySymbols = computed(() => props.deck.hero_card.symbols.filter((symbol) => symbol.symbol_type === 'affinity'));
const uppercaseFirstCharacter = (value: string): string =>
  value.length === 0 ? value : value[0].toLocaleUpperCase() + value.slice(1);
const ownerDisplayName = computed(() => uppercaseFirstCharacter(props.deck.owner.username));
const titlePillLabel = computed(() => (isOwnedMode.value ? deckVisibilityLabels[props.deck.visibility] : ownerDisplayName.value));
const titlePillClass = computed(() => (isOwnedMode.value ? deckVisibilityBadgeClasses[props.deck.visibility] : 'theme-pill-keyword'));
const deprecatedCardCount = computed(() => props.deck.status.deprecated_card_count ?? 0);
const cardClass = computed(() => [
  'deck-list-card-surface',
  'page-card',
  isBrowseMode.value ? 'deck-list-card-browse' : 'deck-list-card-owned',
  isCompact.value ? 'deck-list-card-compact' : '',
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

const exportDeck = async (close: () => void): Promise<void> => {
  await exportTtsDeck(props.deck.id, props.deck.name);
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
  --deck-card-art-width: min(21rem, 64%);
  --deck-card-art-mask: linear-gradient(90deg, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 0.98) 42%, rgba(0, 0, 0, 0.72) 58%, rgba(0, 0, 0, 0.28) 74%, rgba(0, 0, 0, 0.08) 86%, transparent 100%);
  --deck-card-art-position: 23% 10%;
  --deck-card-art-scale: 1.2;
  --deck-card-art-hover-scale: 1.27;
  --deck-card-art-hover-shift-x: 0.2rem;
  --deck-card-content-padding-left: clamp(19.5rem, 21%, 11rem);
  position: relative;
  height: 14.5rem;
  overflow: hidden;
  padding: 0;
}

.deck-list-card-art {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--deck-card-art-width);
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(148, 163, 184, 0.26), transparent 55%),
    linear-gradient(135deg, rgba(30, 41, 59, 0.96), rgba(15, 23, 42, 0.92));
  -webkit-mask-image: var(--deck-card-art-mask);
  mask-image: var(--deck-card-art-mask);
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

.deck-list-card-art-overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(15, 23, 42, 0.04) 0%, rgba(15, 23, 42, 0.08) 38%, rgba(15, 23, 42, 0.22) 56%, rgba(15, 23, 42, 0.1) 70%, transparent 100%),
    linear-gradient(180deg, rgba(15, 23, 42, 0.08), rgba(15, 23, 42, 0.04));
  pointer-events: none;
}

.deck-list-card-content {
  position: relative;
  z-index: 1;
  display: flex;
  height: 100%;
  min-width: 0;
  flex-direction: column;
  padding: 1.1rem 1.2rem 1.1rem var(--deck-card-content-padding-left);
}

.deck-list-card-description {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.deck-list-card-compact {
  --deck-card-art-width: min(13rem, 58%);
  --deck-card-art-position: 28% 12%;
  --deck-card-art-scale: 1.14;
  --deck-card-art-hover-scale: 1.2;
  --deck-card-content-padding-left: clamp(8rem, 34%, 10rem);
  height: 10.5rem;
}

.deck-list-card-compact .deck-list-card-content {
  padding: 0.9rem 1rem 0.85rem var(--deck-card-content-padding-left);
}

.deck-list-card-compact :deep(.theme-section-title.text-lg) {
  font-size: 0.98rem;
  line-height: 1.25rem;
}

@media (max-width: 767px) {
  .deck-list-card-surface {
    --deck-card-art-width: min(15rem, 70%);
    --deck-card-content-padding-left: clamp(5.4rem, 24%, 7.5rem);
    height: 12rem;
  }

  .deck-list-card-content {
    padding: 0.95rem 1rem 0.95rem var(--deck-card-content-padding-left);
  }
}
</style>
