<template>
  <CollectionListCard
    :title="deck.name"
    :description="deck.description"
    :image-url="deck.hero_card.image_url ? toAbsoluteApiUrl(deck.hero_card.image_url) : null"
    :image-alt="deck.hero_card.name"
    :to="titleTo"
    :variant="mode === 'browse' ? 'browse' : 'owned'"
  >
    <template #title-extra>
      <span
        v-if="deprecatedCardCount > 0"
        class="theme-pill theme-pill-warning inline-flex shrink-0 items-center gap-1 px-2 py-1 text-xs"
        title="Deck contains deprecated cards"
      >
        <TriangleAlert class="h-3.5 w-3.5" />
        <span>{{ deprecatedCardCount }}</span>
      </span>
    </template>
    <template #badge>
      <span
        class="collection-list-card-title-pill theme-pill shrink-0 text-xs"
        :class="titlePillClass"
      >
        {{ titlePillLabel }}
      </span>
    </template>
    <template #actions>
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
    </template>
    <template #tags>
      <DeckTagPills
        class="collection-list-card-tags"
        :tags="deck.tags ?? []"
        :pending-suggestions="isOwnedMode ? (deck.pending_tag_suggestions ?? []) : []"
        :max-visible="6"
      />
    </template>
    <template #footer>
      <div class="collection-list-card-footer-meta theme-section-muted text-xs">
        <span class="collection-list-card-footer-meta-item">
          <LibraryBig
            class="h-4 w-4"
            aria-hidden="true"
          />
          <span>Maindeck {{ deck.mainboard.total_cards }}</span>
        </span>
        <span class="collection-list-card-footer-meta-item">
          <Copy
            class="h-4 w-4"
            aria-hidden="true"
          />
          <span>Unique {{ deck.mainboard.unique_cards }}</span>
        </span>
        <span class="collection-list-card-footer-meta-item">
          <PanelRight
            class="h-4 w-4"
            aria-hidden="true"
          />
          <span>Sideboards {{ sideboardCount }}</span>
        </span>
        <span
          v-if="difficultyLabel"
          class="collection-list-card-footer-meta-item"
          data-testid="deck-difficulty"
        >
          <Gauge
            class="h-4 w-4"
            aria-hidden="true"
          />
          <span>Difficulty · {{ difficultyLabel }}</span>
        </span>
        <span class="collection-list-card-footer-meta-item">
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
    </template>
  </CollectionListCard>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import CollectionListCard from '@/shared/components/CollectionListCard.vue';
import {
  CalendarDays,
  Copy,
  Gamepad2,
  Gauge,
  LibraryBig,
  PanelRight,
  Share2,
  TriangleAlert,
} from 'lucide-vue-next';
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
const formatDate = (value: string): string => {
  const date = new Date(value);
  return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()}`;
};
const sideboardCount = computed(() =>
  'sideboard_count' in props.deck ? props.deck.sideboard_count : props.deck.sideboards.length,
);
const heroAffinitySymbols = computed(() =>
  props.deck.hero_card.symbols.filter((symbol) => symbol.symbol_type === 'affinity'),
);
const ownerDisplayName = computed(() => formatDeckOwnerName(props.deck.owner.username));
const titlePillLabel = computed(() =>
  isOwnedMode.value ? deckVisibilityLabels[props.deck.visibility] : ownerDisplayName.value,
);
const titlePillClass = computed(() =>
  isOwnedMode.value ? deckVisibilityBadgeClasses[props.deck.visibility] : 'theme-pill-neutral',
);
const deprecatedCardCount = computed(() => props.deck.status.deprecated_card_count ?? 0);
const difficultyLabel = computed(() =>
  props.deck.difficulty ? deckDifficultyLabels[props.deck.difficulty] : null,
);
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
</script>
