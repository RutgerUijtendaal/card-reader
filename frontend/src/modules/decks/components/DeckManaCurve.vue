<template>
  <section
    :class="containerClass"
  >
    <div
      class="flex items-start justify-between gap-3"
      :class="compact ? 'space-y-0' : ''"
    >
      <div class="space-y-1">
        <h4
          class="theme-section-title font-semibold"
          :class="compact ? 'text-[11px] uppercase tracking-[0.16em]' : 'text-sm'"
        >
          {{ title }}
        </h4>
        <p
          class="theme-section-muted"
          :class="compact ? 'text-[10px]' : 'text-xs'"
        >
          {{ totalCardsLabel }}
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
      class="grid grid-cols-8"
      :class="compact ? 'gap-0.5' : 'gap-2'"
    >
      <div
        v-for="bucket in curveSummary.buckets"
        :key="bucket.label"
        :class="compact ? 'space-y-0.5' : 'space-y-2'"
      >
        <div
          class="flex items-end"
          :class="compact ? 'h-10' : 'h-28'"
        >
          <div
            class="mana-curve-bar w-full rounded-t-lg"
            :class="bucket.count > 0 ? 'mana-curve-bar-filled' : 'mana-curve-bar-empty'"
            :style="{ height: `${Math.max(bucket.heightRatio * 100, bucket.count > 0 ? 14 : 6)}%` }"
          />
        </div>
        <div
          class="text-center"
          :class="compact ? 'space-y-0.5' : 'space-y-1'"
        >
          <p
            class="theme-section-title font-semibold"
            :class="compact ? 'text-[11px]' : 'text-sm'"
          >
            {{ bucket.count }}
          </p>
          <p
            class="theme-kicker font-semibold uppercase tracking-wide"
            :class="compact ? 'text-[8px]' : 'text-[11px]'"
          >
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
import { buildManaCurve, type ManaCurveCardLike, type ManaCurveEntryLike } from '@/modules/decks/manaCurve';

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
const emptyStateLabel = computed(() =>
  curveSummary.value.totalCards > 0 && curveSummary.value.uncostedCards === curveSummary.value.totalCards
    ? 'No mana cost data is available for these cards.'
    : props.emptyLabel,
);
const containerClass = computed(() =>
  props.compact ? 'deck-mana-curve-compact space-y-1.5 rounded-xl border px-2.5 py-2' : 'theme-muted-panel space-y-4 p-4',
);
</script>

<style scoped>
.deck-mana-curve-compact {
  border-color: var(--color-border);
  background: color-mix(in srgb, var(--color-surface-soft) 72%, transparent 28%);
}

.mana-curve-bar {
  transition:
    height 180ms ease,
    background 180ms ease,
    border-color 180ms ease;
  border: 1px solid var(--color-border);
}

.mana-curve-bar-filled {
  background: linear-gradient(180deg, color-mix(in srgb, var(--color-primary-to) 84%, white 16%) 0%, var(--color-primary-from) 100%);
  border-color: color-mix(in srgb, var(--color-primary-from) 40%, var(--color-border) 60%);
}

.mana-curve-bar-empty {
  background: var(--color-surface-soft);
}
</style>
