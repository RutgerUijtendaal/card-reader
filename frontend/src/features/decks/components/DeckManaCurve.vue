<template>
  <section
    :class="containerClass"
  >
    <div
      v-if="showHeader"
      class="flex items-center justify-between gap-3"
    >
      <div
        class="min-w-0"
        :class="compact ? '' : 'flex items-baseline gap-2'"
      >
        <h4
          class="theme-section-title font-semibold"
          :class="compact ? 'text-sm' : 'text-base'"
        >
          {{ title }}
        </h4>
        <p
          v-if="!compact"
          class="theme-section-muted text-sm"
        >
          - {{ totalCardsLabel }}
        </p>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <span
          v-if="curveSummary.uncostedCards > 0"
          class="theme-pill theme-pill-warning shrink-0"
          :class="compact ? 'px-1.5 py-0.5 text-[9px]' : 'text-[10px]'"
        >
          {{ curveSummary.uncostedCards }} without cost
        </span>
        <slot name="header-actions" />
      </div>
    </div>

    <div
      v-if="hasVisibleCurve"
      :class="chartShellClass"
    >
      <div
        :class="chartGridClass"
        :style="chartGridStyle"
      >
        <div
          v-for="bucket in curveSummary.buckets"
          :key="bucket.label"
          :class="bucketColumnClass"
        >
          <p
            class="text-center font-semibold tabular-nums"
            :class="bucket.count > 0 ? countClass : zeroCountClass"
          >
            {{ bucket.count }}
          </p>
          <div :class="barTrackClass">
            <div
              class="mana-curve-bar w-full"
              :class="bucket.count > 0 ? filledBarClass : emptyBarClass"
              :style="barStyle(bucket.count, bucket.heightRatio)"
            />
          </div>
          <p :class="labelClass">
            {{ bucket.label }}
          </p>
        </div>
      </div>
    </div>

    <div
      v-else
      class="theme-empty-state"
      :class="compact ? 'px-2 py-3 text-xs' : ''"
    >
      {{ emptyStateLabel }}
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { buildManaCurve, type ManaCurveCardLike, type ManaCurveEntryLike } from '@/domain/decks/utils/manaCurve';

const props = withDefaults(
  defineProps<{
    entries: ManaCurveEntryLike<ManaCurveCardLike>[];
    title?: string;
    emptyLabel?: string;
    compact?: boolean;
  }>(),
  {
    title: 'Mana Curve',
    emptyLabel: 'No cards in this list yet.',
    compact: false,
  },
);

const curveSummary = computed(() => buildManaCurve(props.entries));
const hasVisibleCurve = computed(() => curveSummary.value.maxBucketCount > 0);
const totalCardsLabel = computed(() => (curveSummary.value.totalCards === 1 ? '1 card' : `${curveSummary.value.totalCards} cards`));
const showHeader = computed(() => !props.compact);
const emptyStateLabel = computed(() =>
  curveSummary.value.totalCards === 0 && curveSummary.value.excludedManaCards > 0
    ? 'No non-mana cards to chart.'
    : curveSummary.value.totalCards > 0 && curveSummary.value.uncostedCards === curveSummary.value.totalCards
    ? 'No mana cost data is available for these cards.'
    : props.emptyLabel,
);
const containerClass = computed(() =>
  props.compact ? '' : 'space-y-4',
);
const chartShellClass = computed(() =>
  props.compact
    ? 'deck-mana-curve-shell-compact px-1 py-1'
    : 'deck-mana-curve-shell px-1 py-2',
);
const chartGridClass = computed(() => (props.compact ? 'grid gap-1' : 'grid gap-2'));
const chartGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${curveSummary.value.buckets.length}, minmax(0, 1fr))`,
}));
const bucketColumnClass = computed(() => (props.compact ? 'space-y-1' : 'space-y-1.5'));
const countClass = computed(() => (props.compact ? 'theme-section-title text-[10px]' : 'theme-section-title text-xs'));
const zeroCountClass = computed(() => (props.compact ? 'theme-kicker text-[10px]' : 'theme-kicker text-xs'));
const labelClass = computed(() =>
  props.compact
    ? 'theme-kicker text-center text-[9px] font-medium uppercase tracking-[0.14em]'
    : 'theme-kicker text-center text-[11px] font-semibold uppercase tracking-[0.16em]',
);
const barTrackClass = computed(() =>
  props.compact
    ? 'theme-divider flex h-12 items-end justify-center border-b pb-1'
    : 'theme-divider flex h-20 items-end justify-center border-b pb-1',
);
const filledBarClass = computed(() => (props.compact ? 'mana-curve-bar-filled-compact' : 'mana-curve-bar-filled'));
const emptyBarClass = computed(() => (props.compact ? 'mana-curve-bar-empty-compact' : 'mana-curve-bar-empty'));
const barStyle = (count: number, heightRatio: number): Record<string, string> => ({
  height: `${Math.max(heightRatio * 100, count > 0 ? (props.compact ? 12 : 10) : props.compact ? 3 : 2)}%`,
});
</script>

<style scoped>
.deck-mana-curve-shell,
.deck-mana-curve-shell-compact {
  background: transparent;
}

.mana-curve-bar {
  max-width: 0.75rem;
  transition:
    height 180ms ease,
    background 180ms ease,
    border-color 180ms ease;
  border-radius: 999px 999px 2px 2px;
}

.mana-curve-bar-filled {
  background: color-mix(in srgb, var(--color-primary-to) 78%, var(--color-text) 22%);
}

.mana-curve-bar-filled-compact {
  background: color-mix(in srgb, var(--color-primary-to) 72%, var(--color-text) 28%);
}

.mana-curve-bar-empty {
  background: color-mix(in srgb, var(--color-border) 42%, transparent 58%);
}

.mana-curve-bar-empty-compact {
  background: color-mix(in srgb, var(--color-border) 38%, transparent 62%);
}

@media (prefers-reduced-motion: reduce) {
  .mana-curve-bar {
    transition-duration: 0.01ms;
  }
}
</style>
