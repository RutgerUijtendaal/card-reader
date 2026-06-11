<template>
  <div
    class="card-detail-loading grid min-h-full items-start gap-6"
    :class="mode === 'editor'
      ? 'xl:h-full xl:min-h-0 xl:grid-cols-[minmax(0,1fr)_minmax(30rem,40vw)] xl:items-stretch xl:overflow-hidden'
      : '2xl:grid-cols-[minmax(0,1fr)_minmax(28rem,35vw)]'"
    aria-label="Loading card detail"
    aria-busy="true"
  >
    <div class="min-w-0 space-y-6">
      <nav
        v-if="showPager"
        class="card-detail-loading-pager theme-divider flex flex-col gap-3 border-b pb-4 sm:flex-row sm:items-center sm:justify-between"
        aria-hidden="true"
      >
        <span class="card-detail-loading-line h-3 w-20" />
        <div class="flex flex-wrap gap-2">
          <span class="card-detail-loading-button h-10 w-36" />
          <span class="card-detail-loading-button h-10 w-32" />
        </div>
      </nav>

      <section
        class="grid items-start gap-6 2xl:grid-cols-[minmax(18rem,30rem)_minmax(24rem,1fr)]"
        aria-hidden="true"
      >
        <div class="p-4">
          <div class="card-detail-loading-card mx-auto block max-h-[44rem] w-full">
            <CardLoadingSkeleton />
          </div>
        </div>

        <div class="space-y-6">
          <div class="space-y-3">
            <span class="card-detail-loading-line h-7 w-72 max-w-full" />
            <span class="card-detail-loading-line h-3 w-48 max-w-[72%]" />
          </div>

          <div class="space-y-5">
            <div class="card-detail-loading-panel h-20" />

            <div class="grid gap-4 sm:grid-cols-2">
              <div class="card-detail-loading-panel h-28" />
              <div class="card-detail-loading-panel h-28" />
            </div>

            <div class="space-y-3">
              <span class="card-detail-loading-line h-4 w-28" />
              <div class="card-detail-loading-panel space-y-3 p-4">
                <span class="card-detail-loading-line h-4 w-full" />
                <span class="card-detail-loading-line h-4 w-5/6" />
                <span class="card-detail-loading-line h-4 w-2/3" />
              </div>
            </div>

            <div class="grid gap-4 sm:grid-cols-2">
              <div class="card-detail-loading-panel h-20" />
              <div class="card-detail-loading-panel h-20" />
            </div>

            <div class="grid gap-4 sm:grid-cols-2">
              <div class="card-detail-loading-panel h-28" />
              <div class="card-detail-loading-panel h-28" />
            </div>
          </div>
        </div>
      </section>

      <section
        class="border-t border-[var(--color-border)] py-2 pt-6"
        aria-hidden="true"
      >
        <div class="mb-2 space-y-1">
          <span class="card-detail-loading-line h-3 w-24" />
          <span class="card-detail-loading-line h-3 w-56 max-w-full" />
        </div>
        <div class="grid gap-2 sm:grid-cols-2 2xl:grid-cols-3">
          <div
            v-for="index in 2"
            :key="`printing-loading-${index}`"
            class="card-detail-loading-printing group relative flex min-w-0 items-center gap-3 rounded-lg border px-2.5 py-2 text-left"
            :class="index === 1 ? 'theme-selected-surface-strong' : 'theme-card-frame theme-section-title'"
          >
            <div class="card-detail-loading-thumb theme-card-frame-muted theme-card-image-well h-16 w-12 shrink-0 rounded-md">
              <CardLoadingSkeleton />
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="card-detail-loading-line h-4 w-24 max-w-[50%]" />
                <span class="card-detail-loading-pill h-5 w-12" />
              </div>
              <span class="card-detail-loading-line mt-2 h-3 w-20" />
              <span class="card-detail-loading-line mt-2 h-3 w-24" />
            </div>
          </div>
        </div>
      </section>
    </div>

    <aside
      class="min-w-0"
      :class="mode === 'editor'
        ? 'xl:h-full xl:min-h-0 xl:border-l xl:border-[var(--color-border)] xl:pl-6'
        : '2xl:sticky 2xl:top-0 2xl:h-[calc(100vh-3rem)] 2xl:max-h-[calc(100vh-11rem)] 2xl:border-l 2xl:border-[var(--color-border)] 2xl:pl-6'"
      aria-hidden="true"
    >
      <div
        class="2xl:app-scrollbar 2xl:h-full 2xl:overflow-y-auto 2xl:pr-1"
        :class="mode === 'editor' ? 'space-y-5' : 'space-y-3'"
      >
        <template v-if="mode === 'editor'">
          <div class="space-y-3">
            <span class="card-detail-loading-line h-5 w-40" />
            <span class="card-detail-loading-line h-3 w-64 max-w-full" />
          </div>

          <div class="grid grid-cols-2 gap-2">
            <div class="card-detail-loading-panel h-10" />
            <div class="card-detail-loading-panel h-10" />
          </div>

          <div
            v-for="index in 6"
            :key="`editor-loading-${index}`"
            class="space-y-2"
          >
            <span class="card-detail-loading-line h-3 w-24" />
            <div class="card-detail-loading-panel h-11" />
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <span class="card-detail-loading-action h-10 w-28" />
            <span class="card-detail-loading-action h-10 w-32" />
          </div>
        </template>

        <template v-else>
          <div class="space-y-2">
            <span class="card-detail-loading-line h-4 w-44" />
            <span class="card-detail-loading-line h-2.5 w-72 max-w-full" />
          </div>
          <div class="card-detail-loading-deck-reference">
            <DeckLoadingSkeleton />
          </div>
        </template>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import CardLoadingSkeleton from '@/components/cards/CardLoadingSkeleton.vue';
import DeckLoadingSkeleton from '@/components/decks/DeckLoadingSkeleton.vue';

defineProps<{
  mode: 'public' | 'editor';
  showPager?: boolean;
}>();
</script>

<style scoped>
.card-detail-loading-line,
.card-detail-loading-panel,
.card-detail-loading-action,
.card-detail-loading-button,
.card-detail-loading-pill {
  position: relative;
  display: block;
  overflow: hidden;
  background: var(--color-surface-muted);
}

.card-detail-loading-printing {
  position: relative;
  overflow: hidden;
  background: var(--color-surface-muted);
}

.card-detail-loading-line,
.card-detail-loading-action,
.card-detail-loading-button,
.card-detail-loading-pill {
  border-radius: 0.35rem;
}

.card-detail-loading-panel {
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
}

.card-detail-loading-printing .card-detail-loading-line,
.card-detail-loading-printing .card-detail-loading-pill {
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--color-text) 22%, var(--color-surface-strong) 78%) 0%,
    color-mix(in srgb, var(--theme-accent) 34%, var(--color-surface-strong) 66%) 100%
  );
}

.card-detail-loading-card {
  max-width: 30rem;
}

.card-detail-loading-thumb {
  overflow: hidden;
  border-radius: 0.375rem;
}

.card-detail-loading-thumb :deep(.theme-card-loading-shim) {
  width: 100%;
  height: 100%;
}

.card-detail-loading-thumb :deep(.theme-card-loading-shim-frame) {
  height: 100%;
  min-height: 0;
  border-radius: 0.375rem;
}

.card-detail-loading-thumb :deep(.theme-card-loading-shim-bar),
.card-detail-loading-thumb :deep(.theme-card-loading-shim-rules) {
  display: none;
}

.card-detail-loading-deck-reference :deep(.deck-loading-skeleton-shell) {
  width: 100%;
}

.card-detail-loading-line::after,
.card-detail-loading-panel::after,
.card-detail-loading-action::after,
.card-detail-loading-button::after,
.card-detail-loading-pill::after,
.card-detail-loading-printing::after {
  position: absolute;
  inset: 0;
  content: '';
  background: linear-gradient(
    90deg,
    transparent 0%,
    color-mix(in srgb, var(--color-surface-strong) 58%, transparent) 48%,
    transparent 100%
  );
  animation: card-detail-loading-sheen 1.6s ease-in-out infinite;
  transform: translateX(-100%);
}

@keyframes card-detail-loading-sheen {
  to {
    transform: translateX(100%);
  }
}
</style>
