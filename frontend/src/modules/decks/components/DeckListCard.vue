<template>
  <component
    :is="rootTag"
    v-bind="rootProps"
    :class="layoutClass"
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
                :class="deck.is_public ? 'theme-pill-accent' : 'theme-pill-neutral'"
              >
                {{ deck.is_public ? 'Public' : 'Private' }}
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
              class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm"
            >
              <span class="theme-section-muted">
                <span class="theme-section-title font-medium">Total</span>
                {{ deck.totals.overall_total_cards }}
              </span>
              <span class="theme-section-muted">
                <span class="theme-section-title font-medium">Main</span>
                {{ deck.mainboard.total_cards }} / {{ MIN_MAINBOARD_CARD_COUNT }}+
              </span>
              <span class="theme-section-muted">
                <span class="theme-section-title font-medium">Unique</span>
                {{ deck.totals.overall_unique_cards }}
              </span>
              <span class="theme-section-muted">
                <span class="theme-section-title font-medium">Status</span>
                {{ deck.status.label }}
              </span>
            </div>

            <p class="theme-section-muted mt-1 text-sm">
              Hero: {{ deck.hero_card.name }}
            </p>
            <p
              v-if="mode === 'browse'"
              class="theme-section-muted text-sm"
            >
              By {{ deck.owner.username }}
            </p>
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
              class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]"
            >
              Updated {{ formatDate(deck.updated_at) }}
            </p>
          </div>
        </div>
      </div>

      <div :class="curveColumnClass">
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
        class="flex flex-wrap gap-2 lg:shrink-0"
      >
        <slot name="actions" />
      </div>
    </div>
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';
import DeckManaCurve from '@/modules/decks/components/DeckManaCurve.vue';
import { MIN_MAINBOARD_CARD_COUNT } from '@/modules/decks/constants';
import type { DeckRecord } from '@/modules/decks/types';

const props = defineProps<{
  deck: DeckRecord;
  mode: 'browse' | 'owned';
  titleTo?: string;
}>();

const isCardLink = computed(() => props.mode === 'browse' && Boolean(props.titleTo));
const rootTag = computed(() => (isCardLink.value ? 'RouterLink' : 'div'));
const rootProps = computed(() => (isCardLink.value ? { to: props.titleTo } : {}));
const titleTag = computed(() => (isCardLink.value ? 'h3' : props.titleTo ? 'RouterLink' : 'h3'));
const titleProps = computed(() => (!isCardLink.value && props.titleTo ? { to: props.titleTo } : {}));
const formatDate = (value: string): string => new Date(value).toLocaleDateString();
const layoutClass = computed(() => [
  'page-card',
  props.mode === 'browse'
    ? 'block transition hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--theme-surface)]'
    : '',
]);
const contentLayoutClass = computed(() =>
  props.mode === 'owned'
    ? 'flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between'
    : 'flex flex-col gap-4 xl:flex-row xl:items-start',
);
const mainColumnClass = computed(() => 'min-w-0 flex-1');
const mediaRowClass = computed(() => (props.mode === 'browse' ? 'flex min-w-0 gap-4' : 'flex min-w-0 gap-4'));
const imageFrameClass = computed(() => (props.mode === 'browse' ? 'h-36 w-28' : 'h-32 w-24'));
const curveColumnClass = computed(() => (props.mode === 'browse' ? 'w-full xl:w-[13rem] xl:shrink-0' : 'w-full xl:w-[16.5rem] xl:shrink-0'));
</script>
