<template>
  <div
    v-if="isBrowseMode"
    class="deck-list-card-browse-shell"
  >
    <div
      :class="browseCardClass"
      :data-navigation-target="titleTo"
      @click="handleCardClick"
      @keydown.enter="handleCardKeydown"
      @keydown.space.prevent="handleCardKeydown"
    >
      <div class="deck-list-card-browse-art">
        <img
          v-if="deck.hero_card.image_url"
          :src="toAbsoluteApiUrl(deck.hero_card.image_url)"
          :alt="deck.hero_card.name"
          class="deck-list-card-browse-art-image"
        >
        <div
          v-else
          class="deck-list-card-browse-art-fallback"
          aria-hidden="true"
        />
        <div
          class="deck-list-card-browse-art-overlay"
          aria-hidden="true"
        />
      </div>

      <div class="deck-list-card-browse-content">
        <div class="flex items-start gap-3">
          <div class="min-w-0 flex-1 space-y-3">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="theme-section-title truncate text-lg font-semibold">
                {{ deck.name }}
              </h3>
              <span class="theme-pill theme-pill-keyword shrink-0 text-xs">
                {{ deck.owner.username }}
              </span>
            </div>

            <p class="theme-section-muted text-sm">
              Hero: {{ deck.hero_card.name }}
            </p>

            <p class="theme-section-muted text-sm">
              {{ boardSummary }}
            </p>

            <p
              v-if="deck.description"
              class="deck-list-card-browse-description theme-section-title text-sm"
            >
              {{ deck.description }}
            </p>
            <p
              v-else
              class="deck-list-card-browse-description theme-section-muted text-sm"
            >
              No description available.
            </p>
          </div>

          <div
            class="shrink-0"
            data-card-click-ignore="true"
          >
            <ExtraActionsMenu button-label="Open deck actions">
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

  <component
    :is="rootTag"
    v-else
    v-bind="rootProps"
    :class="ownedLayoutClass"
    @click="handleCardClick"
    @keydown.enter="handleCardKeydown"
    @keydown.space.prevent="handleCardKeydown"
  >
    <div :class="contentLayoutClass">
      <div :class="mainColumnClass">
        <div :class="mediaRowClass">
          <div
            class="theme-card-frame-muted theme-card-image-well flex shrink-0 items-center justify-center rounded-xl"
            :class="imageFrameClass"
          >
            <img
              v-if="deck.hero_card.image_url"
              :src="toAbsoluteApiUrl(deck.hero_card.image_url)"
              :alt="deck.hero_card.name"
              class="h-full w-full object-contain"
            >
            <div
              v-else
              class="theme-kicker text-xs"
            >
              No image
            </div>
          </div>

          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <component
                :is="titleTag"
                v-bind="titleProps"
                class="theme-section-title text-lg font-semibold"
                :class="titleTo ? 'truncate' : ''"
              >
                {{ deck.name }}
              </component>
              <span
                class="theme-pill text-xs"
                :class="visibilityBadgeClass"
              >
                {{ visibilityLabel }}
              </span>
            </div>

            <div class="theme-section-muted mt-2 space-y-1 text-sm">
              <p><span class="theme-section-title font-medium">Hero</span> {{ deck.hero_card.name }}</p>
              <p><span class="theme-section-title font-medium">Total / Main</span> {{ deck.totals.overall_total_cards }} / {{ deck.mainboard.total_cards }}</p>
              <p><span class="theme-section-title font-medium">Unique</span> {{ deck.totals.overall_unique_cards }}</p>
              <p><span class="theme-section-title font-medium">Side Decks</span> {{ deck.sideboards.length }}</p>
              <p><span class="theme-section-title font-medium">Status</span> {{ deck.status.label }}</p>
            </div>

            <p
              v-if="deck.status.issues.length > 0"
              class="theme-section-muted mt-1 text-sm"
            >
              {{ deck.status.issues[0] }}
            </p>
            <p
              v-if="deck.description"
              class="theme-section-title mt-2 text-sm"
            >
              {{ deck.description }}
            </p>
          </div>
        </div>
      </div>

      <div
        v-if="$slots.actions"
        :class="actionsColumnClass"
        data-card-click-ignore="true"
      >
        <slot name="actions" />
      </div>
    </div>
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { toast } from 'vue-sonner';
import { toAbsoluteApiUrl } from '@/api/client';
import SymbolToken from '@/components/SymbolToken.vue';
import ExtraActionsMenu from '@/components/app/ExtraActionsMenu.vue';
import { buildDeckShareUrl, canShareDeck } from '@/modules/decks/share';
import type { DeckRecord } from '@/modules/decks/types';
import { useDeckExport } from '@/modules/decks/useDeckExport';
import { deckVisibilityBadgeClasses, deckVisibilityLabels } from '@/modules/decks/visibility';

const props = defineProps<{
  deck: DeckRecord;
  mode: 'browse' | 'owned';
  titleTo?: string;
}>();

const router = useRouter();
const { exportTtsDeck } = useDeckExport();

const isBrowseMode = computed(() => props.mode === 'browse');
const isClickableCard = computed(() => Boolean(props.titleTo));
const visibilityLabel = computed(() => deckVisibilityLabels[props.deck.visibility]);
const visibilityBadgeClass = computed(() => deckVisibilityBadgeClasses[props.deck.visibility]);
const rootTag = computed(() => (props.titleTo ? 'div' : 'div'));
const rootProps = computed(() => {
  if (!props.titleTo) {
    return {};
  }

  return {
    role: 'link',
    tabindex: 0,
  };
});
const titleTag = computed(() => (props.titleTo ? 'RouterLink' : 'h3'));
const titleProps = computed(() => (props.titleTo ? { to: props.titleTo } : {}));
const formatDate = (value: string): string => new Date(value).toLocaleDateString();
const sideboardSummary = computed(() => {
  if (props.deck.sideboards.length === 0) {
    return 'No sideboards';
  }
  return `${props.deck.sideboards.length} sideboard${props.deck.sideboards.length === 1 ? '' : 's'}`;
});
const boardSummary = computed(() => `Maindeck ${props.deck.mainboard.total_cards} · ${props.deck.mainboard.unique_cards} unique · ${sideboardSummary.value}`);
const heroAffinitySymbols = computed(() => props.deck.hero_card.symbols.filter((symbol) => symbol.symbol_type === 'affinity'));
const browseCardClass = computed(() => [
  'deck-list-card-browse',
  'page-card',
  isClickableCard.value
    ? 'cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--theme-surface)]'
    : '',
]);
const ownedLayoutClass = computed(() => [
  'deck-list-card',
  'page-card',
  props.titleTo
    ? 'block cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--theme-surface)]'
    : '',
]);
const contentLayoutClass = computed(() =>
  'grid gap-4 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-stretch',
);
const mainColumnClass = computed(() => 'min-w-0 flex-1');
const mediaRowClass = computed(() => 'flex min-w-0 gap-4');
const imageFrameClass = computed(() => 'h-44 w-31');
const actionsColumnClass = computed(() =>
  'theme-divider flex h-full items-stretch justify-end xl:border-l xl:pl-4',
);

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
.deck-list-card-browse-shell {
  min-width: 0;
}

.deck-list-card-browse {
  --deck-browse-art-width: min(21rem, 64%);
  --deck-browse-art-mask: linear-gradient(90deg, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 0.98) 42%, rgba(0, 0, 0, 0.72) 58%, rgba(0, 0, 0, 0.28) 74%, rgba(0, 0, 0, 0.08) 86%, transparent 100%);
  --deck-browse-art-position: 23% 10%;
  --deck-browse-art-scale: 1.2;
  --deck-browse-art-hover-scale: 1.27;
  --deck-browse-art-hover-shift-x: 0.2rem;
  --deck-browse-content-padding-left: clamp(19.5rem, 21%, 11rem);
  position: relative;
  height: 14.5rem;
  overflow: hidden;
  padding: 0;
}

.deck-list-card-browse-art {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--deck-browse-art-width);
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(148, 163, 184, 0.26), transparent 55%),
    linear-gradient(135deg, rgba(30, 41, 59, 0.96), rgba(15, 23, 42, 0.92));
  -webkit-mask-image: var(--deck-browse-art-mask);
  mask-image: var(--deck-browse-art-mask);
}

.deck-list-card-browse-art-image {
  height: 100%;
  width: 100%;
  object-fit: cover;
  object-position: var(--deck-browse-art-position);
  transform: scale(var(--deck-browse-art-scale));
  transition: transform 240ms ease;
}

.deck-list-card-browse:hover .deck-list-card-browse-art-image,
.deck-list-card-browse:focus-within .deck-list-card-browse-art-image {
  transform: scale(var(--deck-browse-art-hover-scale)) translateX(var(--deck-browse-art-hover-shift-x));
}

.deck-list-card-browse-art-fallback {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top left, rgba(244, 114, 182, 0.32), transparent 45%),
    radial-gradient(circle at bottom left, rgba(59, 130, 246, 0.24), transparent 48%),
    linear-gradient(140deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.96));
}

.deck-list-card-browse-art-overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(15, 23, 42, 0.04) 0%, rgba(15, 23, 42, 0.08) 38%, rgba(15, 23, 42, 0.22) 56%, rgba(15, 23, 42, 0.1) 70%, transparent 100%),
    linear-gradient(180deg, rgba(15, 23, 42, 0.08), rgba(15, 23, 42, 0.04));
  pointer-events: none;
}

.deck-list-card-browse-content {
  position: relative;
  z-index: 1;
  display: flex;
  height: 100%;
  min-width: 0;
  flex-direction: column;
  padding: 1.1rem 1.2rem 1.1rem var(--deck-browse-content-padding-left);
}

.deck-list-card-browse-description {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

@media (max-width: 767px) {
  .deck-list-card-browse {
    --deck-browse-art-width: min(15rem, 70%);
    --deck-browse-content-padding-left: clamp(5.4rem, 24%, 7.5rem);
    height: 12rem;
  }

  .deck-list-card-browse-content {
    padding: 0.95rem 1rem 0.95rem var(--deck-browse-content-padding-left);
  }
}
</style>
