<template>
  <div
    class="grid items-start gap-6 2xl:grid-cols-[minmax(0,1fr)_minmax(28rem,35vw)]"
    aria-label="Loading card group detail"
    aria-busy="true"
  >
    <div class="min-w-0 space-y-6">
      <nav
        v-if="showPager"
        class="theme-divider flex flex-col gap-3 border-b pb-4 sm:flex-row sm:items-center sm:justify-between"
        aria-hidden="true"
      >
        <span class="card-group-loading-line h-3 w-20" />
        <div class="flex flex-wrap gap-2">
          <span class="card-group-loading-button h-10 w-36" />
          <span class="card-group-loading-button h-10 w-32" />
        </div>
      </nav>

      <div class="space-y-6">
        <section
          v-for="index in 2"
          :key="`group-member-loading-${index}`"
          class="space-y-4 border-t border-[var(--color-border)] pt-6 first:border-t-0 first:pt-0"
          aria-hidden="true"
        >
          <div class="flex items-center justify-between gap-3 px-1">
            <div class="flex items-center gap-2">
              <span class="card-group-loading-line h-5 w-40" />
              <span
                v-if="index === 1"
                class="card-group-loading-pill h-5 w-16"
              />
            </div>
            <span class="card-group-loading-line h-4 w-20" />
          </div>

          <section class="grid items-start gap-6 2xl:grid-cols-[minmax(18rem,30rem)_minmax(24rem,1fr)]">
            <div class="p-4">
              <div class="mx-auto block max-h-[44rem] max-w-[30rem]">
                <CardLoadingSkeleton />
              </div>
            </div>

            <div class="space-y-6">
              <div class="space-y-3">
                <span class="card-group-loading-line h-7 w-72 max-w-full" />
                <span class="card-group-loading-line h-3 w-48 max-w-[72%]" />
              </div>

              <div class="space-y-5">
                <div class="card-group-loading-panel h-20" />

                <div class="grid gap-4 sm:grid-cols-2">
                  <div class="card-group-loading-panel h-28" />
                  <div class="card-group-loading-panel h-28" />
                </div>

                <div class="space-y-3">
                  <span class="card-group-loading-line h-4 w-28" />
                  <div class="card-group-loading-panel space-y-3 p-4">
                    <span class="card-group-loading-line h-4 w-full" />
                    <span class="card-group-loading-line h-4 w-5/6" />
                    <span class="card-group-loading-line h-4 w-2/3" />
                  </div>
                </div>

                <div class="grid gap-4 sm:grid-cols-2">
                  <div class="card-group-loading-panel h-20" />
                  <div class="card-group-loading-panel h-20" />
                </div>

                <div class="grid gap-4 sm:grid-cols-2">
                  <div class="card-group-loading-panel h-28" />
                  <div class="card-group-loading-panel h-28" />
                </div>
              </div>
            </div>
          </section>
        </section>
      </div>
    </div>

    <aside
      class="min-w-0 2xl:sticky 2xl:top-6 2xl:h-[calc(100vh-3rem)] 2xl:max-h-[calc(100vh-11rem)] 2xl:border-l 2xl:border-[var(--color-border)] 2xl:pl-6"
      aria-hidden="true"
    >
      <div class="space-y-3 2xl:app-scrollbar 2xl:h-full 2xl:overflow-y-auto 2xl:pr-1">
        <div class="space-y-2">
          <span class="card-group-loading-line h-4 w-44" />
          <span class="card-group-loading-line h-2.5 w-72 max-w-full" />
        </div>
        <DeckLoadingSkeleton />
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import CardLoadingSkeleton from '@/components/cards/CardLoadingSkeleton.vue';
import DeckLoadingSkeleton from '@/components/decks/DeckLoadingSkeleton.vue';

defineProps<{
  showPager?: boolean;
}>();
</script>

<style scoped>
.card-group-loading-line,
.card-group-loading-panel,
.card-group-loading-button,
.card-group-loading-pill {
  position: relative;
  display: block;
  overflow: hidden;
  background: var(--color-surface-muted);
}

.card-group-loading-line,
.card-group-loading-button,
.card-group-loading-pill {
  border-radius: 0.35rem;
}

.card-group-loading-panel {
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
}

.card-group-loading-line::after,
.card-group-loading-panel::after,
.card-group-loading-button::after,
.card-group-loading-pill::after {
  position: absolute;
  inset: 0;
  content: '';
  background: linear-gradient(
    90deg,
    transparent 0%,
    color-mix(in srgb, var(--color-surface-strong) 58%, transparent) 48%,
    transparent 100%
  );
  animation: card-group-loading-sheen 1.6s ease-in-out infinite;
  transform: translateX(-100%);
}

@keyframes card-group-loading-sheen {
  to {
    transform: translateX(100%);
  }
}
</style>
