<template>
  <section
    class="flex flex-col gap-5"
    aria-label="Loading deck detail"
    aria-busy="true"
  >
    <AppPageHeader
      :icon="BookOpenText"
      title="Deck name"
      subtitle="Deck description"
      :back-to="backTo"
      :back-label="backLabel"
      title-tag="h2"
      title-class="deck-detail-loading-header-title text-xl"
      subtitle-class="deck-detail-loading-header-subtitle text-sm"
    >
      <template #titleMeta>
        <div class="flex items-center gap-2">
          <span class="deck-detail-loading-line h-4 w-5" />
          <span class="deck-detail-loading-pill h-6 w-20" />
        </div>
      </template>

      <template #actions>
        <span class="deck-detail-loading-button h-9 w-32" />
        <span class="deck-detail-loading-button h-9 w-28" />
      </template>
    </AppPageHeader>

    <AppPageLayout
      columns="one"
      root-class="xl:grid-cols-[22.5rem_minmax(0,1fr)]"
    >
      <template #aside>
        <AppStickyAside scroll-class="space-y-5">
          <div class="space-y-4">
            <span class="deck-detail-loading-line h-5 w-20" />
            <div class="space-y-3">
              <div class="theme-card-frame theme-card-image-well mx-auto aspect-[63/88] w-full max-w-[22rem] overflow-hidden rounded-2xl">
                <CardLoadingSkeleton />
              </div>
              <span class="deck-detail-loading-line h-6 w-52 max-w-full" />
            </div>
          </div>

          <div class="space-y-3">
            <span class="deck-detail-loading-line h-4 w-28" />
            <div class="theme-muted-panel space-y-2 p-3">
              <div
                v-for="index in 5"
                :key="`curve-loading-${index}`"
                class="flex items-center gap-2"
              >
                <span class="deck-detail-loading-line h-3 w-8" />
                <span
                  class="deck-detail-loading-line h-3"
                  :class="curveWidthClass(index)"
                />
              </div>
            </div>
          </div>

          <div class="theme-divider border-t pt-4">
            <div class="theme-muted-panel flex items-center gap-3 p-3">
              <span
                class="deck-detail-loading-checkbox h-4 w-4 rounded"
                :class="groupByType ? 'deck-detail-loading-checkbox-checked' : ''"
              />
              <span class="deck-detail-loading-line h-4 w-28" />
            </div>
          </div>

          <template #footer>
            <div class="flex flex-wrap items-center gap-3">
              <span class="deck-detail-loading-button h-9 w-32" />
              <span class="deck-detail-loading-button h-9 w-36" />
            </div>
          </template>
        </AppStickyAside>
      </template>

      <section class="space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-2">
            <span class="deck-detail-loading-pill h-7 w-28" />
            <span class="deck-detail-loading-pill h-7 w-24" />
          </div>
          <span class="deck-detail-loading-pill h-7 w-40" />
        </div>

        <div
          v-if="groupByType"
          class="space-y-6 px-1 pb-3 pt-2"
        >
          <section
            v-for="groupIndex in 2"
            :key="`deck-card-loading-group-${groupIndex}`"
            class="space-y-3"
            data-testid="deck-loading-type-group"
          >
            <div class="flex items-center justify-between gap-3">
              <span
                class="deck-detail-loading-line h-5"
                :class="groupIndex === 1 ? 'w-24' : 'w-32'"
              />
              <span class="deck-detail-loading-pill h-7 w-20" />
            </div>
            <div
              class="grid gap-4"
              :style="gridStyle"
            >
              <div
                v-for="index in 4"
                :key="`deck-card-loading-group-${groupIndex}-${index}`"
                class="relative justify-self-center"
                :style="cardStyle"
              >
                <CardLoadingSkeleton />
              </div>
            </div>
          </section>
        </div>

        <div
          v-else
          class="grid gap-4 px-1 pb-3 pt-2"
          :style="gridStyle"
        >
          <div
            v-for="index in 8"
            :key="`deck-card-loading-${index}`"
            class="relative justify-self-center"
            :style="cardStyle"
          >
            <CardLoadingSkeleton />
          </div>
        </div>
      </section>
    </AppPageLayout>
  </section>
</template>

<script setup lang="ts">
import { BookOpenText } from 'lucide-vue-next';
import type { StyleValue } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import AppPageLayout from '@/components/app/AppPageLayout.vue';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import AppStickyAside from '@/components/app/AppStickyAside.vue';
import CardLoadingSkeleton from '@/components/cards/CardLoadingSkeleton.vue';

defineProps<{
  backTo: RouteLocationRaw;
  backLabel: string;
  gridStyle: StyleValue;
  cardStyle: StyleValue;
  groupByType: boolean;
}>();

const curveWidthClass = (index: number): string => {
  const widths = ['w-1/2', 'w-3/4', 'w-2/3', 'w-1/3', 'w-5/6'];
  return widths[index - 1] ?? 'w-1/2';
};
</script>

<style scoped>
.deck-detail-loading-line,
.deck-detail-loading-button,
.deck-detail-loading-pill,
.deck-detail-loading-checkbox {
  position: relative;
  display: block;
  overflow: hidden;
  background: var(--color-surface-muted);
}

.deck-detail-loading-line,
.deck-detail-loading-button,
.deck-detail-loading-pill,
.deck-detail-loading-checkbox {
  border-radius: 0.4rem;
}

.deck-detail-loading-button,
.deck-detail-loading-pill,
.deck-detail-loading-checkbox {
  border: 1px solid var(--color-border);
}

.deck-detail-loading-line::after,
.deck-detail-loading-button::after,
.deck-detail-loading-pill::after,
.deck-detail-loading-checkbox::after,
:deep(.deck-detail-loading-header-title)::after,
:deep(.deck-detail-loading-header-subtitle)::after {
  position: absolute;
  inset: 0;
  content: '';
  background: linear-gradient(
    90deg,
    transparent 0%,
    color-mix(in srgb, var(--color-surface-strong) 58%, transparent) 48%,
    transparent 100%
  );
  animation: deck-detail-loading-sheen 1.6s ease-in-out infinite;
  transform: translateX(-100%);
}

.deck-detail-loading-checkbox-checked {
  background:
    linear-gradient(135deg, transparent 0 38%, var(--color-accent) 38% 62%, transparent 62% 100%),
    var(--color-surface-muted);
}

:deep(.deck-detail-loading-header-title),
:deep(.deck-detail-loading-header-subtitle) {
  position: relative;
  display: block;
  overflow: hidden;
  color: transparent;
  border-radius: 0.4rem;
  background: var(--color-surface-muted);
}

:deep(.deck-detail-loading-header-title) {
  width: min(18rem, 64vw);
  height: 1.75rem;
}

:deep(.deck-detail-loading-header-subtitle) {
  width: min(26rem, 72vw);
  height: 1.25rem;
}

@keyframes deck-detail-loading-sheen {
  to {
    transform: translateX(100%);
  }
}
</style>
