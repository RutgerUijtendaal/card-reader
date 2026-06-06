<template>
  <section
    :class="containerClass"
  >
    <div
      v-if="showHeader"
      class="flex items-start justify-between gap-3"
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
      <span
        v-if="curveSummary.uncostedCards > 0"
        class="theme-pill theme-pill-warning shrink-0"
        :class="compact ? 'px-1.5 py-0.5 text-[9px]' : 'text-[10px]'"
      >
        {{ curveSummary.uncostedCards }} without cost
      </span>
    </div>

    <div
      v-if="hasVisibleCurve"
      :class="chartShellClass"
    >
      <div :class="chartGridClass">
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
import { buildManaCurve, type ManaCurveCardLike, type ManaCurveEntryLike } from '@/composables/decks/manaCurve';

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
  curveSummary.value.totalCards > 0 && curveSummary.value.uncostedCards === curveSummary.value.totalCards
    ? 'No mana cost data is available for these cards.'
    : props.emptyLabel,
);
const containerClass = computed(() =>
  props.compact ? '' : 'space-y-4',
);
const chartShellClass = computed(() =>
  props.compact
    ? 'deck-mana-curve-shell-compact rounded-lg px-2 py-1.5'
    : 'deck-mana-curve-shell rounded-xl px-3 py-3',
);
const chartGridClass = computed(() => (props.compact ? 'grid grid-cols-8 gap-1.5' : 'grid grid-cols-8 gap-3'));
const bucketColumnClass = computed(() => (props.compact ? 'space-y-1' : 'space-y-2'));
const countClass = computed(() => (props.compact ? 'theme-section-title text-[10px]' : 'theme-section-title text-sm'));
const zeroCountClass = computed(() => (props.compact ? 'theme-kicker text-[10px]' : 'theme-kicker text-sm'));
const labelClass = computed(() =>
  props.compact
    ? 'theme-kicker text-center text-[9px] font-medium uppercase tracking-[0.14em]'
    : 'theme-kicker text-center text-[11px] font-semibold uppercase tracking-[0.16em]',
);
const barTrackClass = computed(() =>
  props.compact
    ? 'flex h-14 items-end border-b pb-1 theme-divider'
    : 'flex h-24 items-end border-b pb-1.5 theme-divider',
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
  border: 1px solid color-mix(in srgb, var(--color-border) 62%, transparent 38%);
  background: color-mix(in srgb, var(--color-surface-soft) 42%, transparent 58%);
}

.mana-curve-bar {
  transition:
    height 180ms ease,
    background 180ms ease,
    border-color 180ms ease;
  border-radius: 6px 6px 0 0;
}

.mana-curve-bar-filled {
  background: linear-gradient(180deg, color-mix(in srgb, var(--color-primary-to) 74%, white 26%) 0%, color-mix(in srgb, var(--color-primary-from) 88%, white 12%) 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.3),
    0 8px 18px rgba(99, 102, 241, 0.12);
}

.mana-curve-bar-filled-compact {
  background: linear-gradient(180deg, color-mix(in srgb, var(--color-primary-to) 72%, white 28%) 0%, color-mix(in srgb, var(--color-primary-from) 84%, white 16%) 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.28),
    0 6px 14px rgba(99, 102, 241, 0.1);
}

.mana-curve-bar-empty {
  background: color-mix(in srgb, var(--color-border) 26%, transparent 74%);
}

.mana-curve-bar-empty-compact {
  background: color-mix(in srgb, var(--color-border) 24%, transparent 76%);
}
</style>
