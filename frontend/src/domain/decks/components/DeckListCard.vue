<template>
  <CollectionListCard
    :title="deck.name"
    :description="deck.description"
    :image-url="deck.hero_card.image_url ? toAbsoluteApiUrl(deck.hero_card.image_url) : null"
    :image-alt="deck.hero_card.name"
    :to="titleTo"
    :variant="mode === 'browse' ? 'browse' : 'owned'"
  >
    <template #badge>
      <span
        class="collection-tile-badge theme-art-chip gap-1.5 px-2 py-0.5 text-xs"
        data-testid="deck-tile-badge"
      >
        <span
          v-if="isOwnedMode"
          class="h-1.5 w-1.5 rounded-full"
          :style="{ background: visibilityDotColor }"
          aria-hidden="true"
        />
        {{ badgeLabel }}
      </span>
    </template>
    <template #actions>
      <slot
        v-if="$slots.actions"
        name="actions"
      />

      <ExtraActionsMenu
        v-else
        button-label="Open deck actions"
        button-class="theme-art-chip h-8 w-8"
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

          <slot
            name="menu-danger-actions"
            :close="close"
          />
        </template>
      </ExtraActionsMenu>
    </template>
    <template
      v-if="heroAffinitySymbols.length > 0"
      #art-corner
    >
      <SymbolToken
        v-for="symbol in heroAffinitySymbols"
        :key="symbol.id"
        :asset-url="symbol.asset_url"
        :label="symbol.label"
        :text-token="symbol.text_token"
        class="h-6 w-6 drop-shadow"
      />
    </template>
    <template #title-extra>
      <span
        v-if="deprecatedCardCount > 0"
        class="theme-pill theme-pill-warning inline-flex shrink-0 items-center gap-1 px-2 py-0.5 text-xs"
        title="Deck contains deprecated cards"
      >
        <TriangleAlert class="h-3.5 w-3.5" />
        <span>{{ deprecatedCardCount }}</span>
      </span>
    </template>
    <template
      v-if="(deck.tags ?? []).length > 0 || (isOwnedMode && (deck.pending_tag_suggestions ?? []).length > 0)"
      #tags
    >
      <DeckTagPills
        :tags="deck.tags ?? []"
        :pending-suggestions="isOwnedMode ? (deck.pending_tag_suggestions ?? []) : []"
        :max-visible="4"
      />
    </template>
    <template #footer>
      <span class="collection-tile-footer-items">
        <span class="collection-tile-footer-item">{{ deck.mainboard.total_cards }} cards</span>
        <span
          v-if="sideboardCount > 0"
          class="collection-tile-footer-item"
        >{{ sideboardCount }} sideboard{{ sideboardCount === 1 ? '' : 's' }}</span>
        <span
          v-if="difficultyLabel"
          class="collection-tile-footer-item"
          data-testid="deck-difficulty"
          :title="`${difficultyLabel} difficulty`"
        >{{ difficultyLabel }}</span>
      </span>
      <span
        v-if="isOwnedMode"
        class="collection-tile-footer-end"
      >Updated {{ formatDate(deck.updated_at) }}</span>
    </template>
  </CollectionListCard>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import CollectionListCard from '@/shared/components/CollectionListCard.vue';
import { Gamepad2, Share2, TriangleAlert } from 'lucide-vue-next';
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
import type { DeckListRecord, DeckVisibility } from '@/domain/decks/types';
import { useDeckExport } from '@/domain/decks/composables/useDeckExport';
import { deckVisibilityLabels } from '@/domain/decks/utils/visibility';

const props = defineProps<{
  deck: DeckListRecord;
  mode: 'browse' | 'owned';
  titleTo?: RouteLocationRaw;
}>();

const router = useRouter();
const { exportTtsDeck } = useDeckExport();

const isOwnedMode = computed(() => props.mode === 'owned');
const formatDate = (value: string): string =>
  new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
const sideboardCount = computed(() =>
  'sideboard_count' in props.deck ? props.deck.sideboard_count : props.deck.sideboards.length,
);
const heroAffinitySymbols = computed(() =>
  props.deck.hero_card.symbols.filter((symbol) => symbol.symbol_type === 'affinity'),
);
const ownerDisplayName = computed(() => formatDeckOwnerName(props.deck.owner.username));
// Browsing names the owner; your own decks show their visibility instead.
const badgeLabel = computed(() =>
  isOwnedMode.value ? deckVisibilityLabels[props.deck.visibility] : ownerDisplayName.value,
);
const VISIBILITY_DOT_COLORS: Record<DeckVisibility, string> = {
  private: 'var(--color-nav-text)',
  unlisted: 'var(--color-pill-warning-text)',
  public: 'var(--color-pill-success-text)',
};
const visibilityDotColor = computed(() => VISIBILITY_DOT_COLORS[props.deck.visibility]);
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
