<template>
  <component
    :is="rootTag"
    v-bind="rootProps"
    :class="layoutClass"
    @click="handleCardClick"
    @keydown.enter="handleCardKeydown"
    @keydown.space.prevent="handleCardKeydown"
  >
    <div :class="contentLayoutClass">
      <div :class="mainColumnClass">
        <div
          :class="mediaRowClass"
        >
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
                :class="isCardLink ? '' : titleTo ? 'truncate' : ''"
              >
                {{ deck.name }}
              </component>
              <span
                v-if="mode === 'owned'"
                class="theme-pill text-xs"
                :class="visibilityBadgeClass"
              >
                {{ visibilityLabel }}
              </span>
              <span
                v-else
                class="theme-pill theme-pill-accent text-xs"
              >
                {{ deck.totals.overall_total_cards }} cards
              </span>
            </div>

            <div
              v-if="mode === 'owned'"
              class="theme-section-muted mt-2 space-y-1 text-sm"
            >
              <p><span class="theme-section-title font-medium">Hero</span> {{ deck.hero_card.name }}</p>
              <p><span class="theme-section-title font-medium">Total / Main</span> {{ deck.totals.overall_total_cards }} / {{ deck.mainboard.total_cards }}</p>
              <p><span class="theme-section-title font-medium">Unique</span> {{ deck.totals.overall_unique_cards }}</p>
              <p><span class="theme-section-title font-medium">Side Decks</span> {{ deck.sideboards.length }}</p>
              <p><span class="theme-section-title font-medium">Status</span> {{ deck.status.label }}</p>
            </div>

            <p
              v-if="mode === 'browse'"
              class="theme-section-muted mt-1 text-sm"
            >
              Hero: {{ deck.hero_card.name }}
            </p>
            <div
              v-if="mode === 'browse'"
              class="theme-section-muted mt-2 flex items-center gap-2 text-sm"
            >
              <span>By</span>
              <span class="theme-pill theme-pill-keyword text-xs">
                {{ deck.owner.username }}
              </span>
            </div>
            <p
              v-else-if="deck.status.issues.length > 0"
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
            <p
              v-if="mode === 'browse'"
              class="theme-kicker mt-2 text-xs font-medium uppercase tracking-[0.16em]"
            >
              Updated {{ formatDate(deck.updated_at) }}
            </p>
          </div>
        </div>
      </div>

      <div
        v-if="mode === 'browse'"
        :class="curveColumnClass"
      >
        <DeckManaCurve
          class="w-full"
          :entries="deck.mainboard.entries"
          title="Curve"
          empty-label="No mainboard cards yet."
          compact
        />
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
import { toAbsoluteApiUrl } from '@/api/client';
import DeckManaCurve from '@/modules/decks/components/DeckManaCurve.vue';
import type { DeckRecord } from '@/modules/decks/types';
import { deckVisibilityBadgeClasses, deckVisibilityLabels } from '@/modules/decks/visibility';

const props = defineProps<{
  deck: DeckRecord;
  mode: 'browse' | 'owned';
  titleTo?: string;
}>();

const router = useRouter();
const isCardLink = computed(() => props.mode === 'browse' && Boolean(props.titleTo));
const isClickableCard = computed(() => props.mode === 'owned' && Boolean(props.titleTo));
const rootTag = computed(() => (isCardLink.value ? 'RouterLink' : 'div'));
const rootProps = computed(() => {
  if (isCardLink.value) {
    return { to: props.titleTo };
  }

  if (isClickableCard.value) {
    return {
      role: 'link',
      tabindex: 0,
    };
  }

  return {};
});
const titleTag = computed(() => (isCardLink.value ? 'h3' : props.titleTo ? 'RouterLink' : 'h3'));
const titleProps = computed(() => (!isCardLink.value && props.titleTo ? { to: props.titleTo } : {}));
const formatDate = (value: string): string => new Date(value).toLocaleDateString();
const visibilityLabel = computed(() => deckVisibilityLabels[props.deck.visibility]);
const visibilityBadgeClass = computed(() => deckVisibilityBadgeClasses[props.deck.visibility]);
const layoutClass = computed(() => [
  'page-card',
  props.titleTo
    ? 'block cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--theme-surface)]'
    : '',
]);
const contentLayoutClass = computed(() =>
  props.mode === 'owned'
    ? 'grid gap-4 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-stretch'
    : 'flex flex-col gap-4 xl:flex-row xl:items-start',
);
const mainColumnClass = computed(() => 'min-w-0 flex-1');
const mediaRowClass = computed(() => (props.mode === 'browse' ? 'flex min-w-0 gap-4' : 'flex min-w-0 gap-4'));
const imageFrameClass = computed(() => (props.mode === 'browse' ? 'h-36 w-28' : 'h-44 w-31'));
const curveColumnClass = computed(() => (props.mode === 'browse' ? 'w-full xl:w-[13rem] xl:shrink-0' : 'w-full xl:w-[16.5rem] xl:shrink-0'));
const actionsColumnClass = computed(() =>
  props.mode === 'owned'
    ? 'theme-divider flex h-full items-stretch justify-end xl:border-l xl:pl-4'
    : 'flex flex-wrap gap-2 lg:shrink-0',
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
  if (!props.titleTo || isCardLink.value) {
    return;
  }
  void router.push(props.titleTo);
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
