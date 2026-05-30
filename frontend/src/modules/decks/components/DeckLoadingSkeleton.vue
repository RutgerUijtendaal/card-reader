<template>
  <div class="deck-loading-skeleton-shell min-w-0">
    <div
      class="deck-loading-skeleton page-card"
      :class="[
        animated ? '' : 'deck-loading-skeleton-static',
        density === 'compact' ? 'deck-loading-skeleton-compact' : '',
      ]"
      aria-hidden="true"
    >
      <div class="deck-loading-skeleton-art">
        <span class="deck-loading-skeleton-image-indicator" />
        <span class="deck-loading-skeleton-art-overlay" />
      </div>

      <div class="deck-loading-skeleton-content">
        <div class="flex items-start gap-4">
          <div class="min-w-0 flex-1 space-y-3">
            <div class="flex flex-wrap items-center gap-2">
              <span class="deck-loading-skeleton-line deck-loading-skeleton-title" />
              <span class="deck-loading-skeleton-pill" />
            </div>

            <span class="deck-loading-skeleton-line deck-loading-skeleton-hero" />
            <span class="deck-loading-skeleton-line deck-loading-skeleton-summary" />

            <div
              v-if="density !== 'compact'"
              class="space-y-2 pt-1"
            >
              <span class="deck-loading-skeleton-line deck-loading-skeleton-description-long" />
              <span class="deck-loading-skeleton-line deck-loading-skeleton-description-short" />
            </div>
          </div>

          <span class="deck-loading-skeleton-actions" />
        </div>

        <div class="mt-auto flex items-end justify-between gap-3 pt-3">
          <span class="deck-loading-skeleton-line deck-loading-skeleton-updated" />
          <div class="flex items-center justify-end gap-1.5">
            <span class="deck-loading-skeleton-symbol" />
            <span class="deck-loading-skeleton-symbol" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  animated?: boolean;
  density?: 'default' | 'compact';
}>(), {
  animated: true,
  density: 'default',
});
</script>

<style scoped>
.deck-loading-skeleton {
  --deck-skeleton-art-width: min(21rem, 64%);
  --deck-skeleton-art-mask: linear-gradient(90deg, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 0.98) 56%, rgba(0, 0, 0, 0.72) 72%, rgba(0, 0, 0, 0.28) 86%, rgba(0, 0, 0, 0.08) 94%, transparent 100%);
  --deck-skeleton-content-padding-left: clamp(19.5rem, 21%, 11rem);
  position: relative;
  height: 14.5rem;
  overflow: hidden;
  padding: 0;
}

.deck-loading-skeleton::after {
  content: '';
  position: absolute;
  inset: 0;
  transform: translateX(-120%);
  background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.18) 50%, transparent 100%);
  animation: deck-loading-skeleton-sheen 1.6s ease-in-out infinite;
  pointer-events: none;
}

.deck-loading-skeleton-static::after {
  display: none;
  animation: none;
}

html.dark .deck-loading-skeleton::after {
  background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.08) 50%, transparent 100%);
}

.deck-loading-skeleton-art {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--deck-skeleton-art-width);
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(148, 163, 184, 0.24), transparent 55%),
    linear-gradient(135deg, color-mix(in srgb, var(--color-surface-strong) 78%, #1e293b 22%), color-mix(in srgb, var(--color-surface-soft) 72%, #0f172a 28%));
  -webkit-mask-image: var(--deck-skeleton-art-mask);
  mask-image: var(--deck-skeleton-art-mask);
}

.deck-loading-skeleton-image-indicator {
  position: absolute;
  inset: 0.5rem 0.7rem 0.5rem 0.5rem;
  display: block;
  border-radius: 0.85rem;
  border: 1px solid color-mix(in srgb, var(--color-border-strong) 58%, transparent 42%);
  background: color-mix(in srgb, var(--color-surface-strong) 78%, transparent 22%);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--color-surface) 64%, transparent 36%);
}

.deck-loading-skeleton-art-overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(15, 23, 42, 0.04) 0%, rgba(15, 23, 42, 0.08) 38%, rgba(15, 23, 42, 0.22) 56%, rgba(15, 23, 42, 0.1) 70%, transparent 100%),
    linear-gradient(180deg, rgba(15, 23, 42, 0.08), rgba(15, 23, 42, 0.04));
}

.deck-loading-skeleton-content {
  position: relative;
  z-index: 1;
  display: flex;
  height: 100%;
  min-width: 0;
  flex-direction: column;
  padding: 1.1rem 1.2rem 1.1rem var(--deck-skeleton-content-padding-left);
}

.deck-loading-skeleton-line,
.deck-loading-skeleton-pill,
.deck-loading-skeleton-actions,
.deck-loading-skeleton-symbol {
  display: block;
  border-radius: 999px;
  background: linear-gradient(90deg, color-mix(in srgb, var(--color-surface-strong) 92%, transparent 8%) 0%, color-mix(in srgb, var(--color-border-strong) 34%, var(--color-surface-strong) 66%) 100%);
}

.deck-loading-skeleton-title {
  width: min(15rem, 58%);
  height: 1.35rem;
}

.deck-loading-skeleton-pill {
  width: 4.6rem;
  height: 1.45rem;
}

.deck-loading-skeleton-hero {
  width: min(18rem, 72%);
  height: 0.9rem;
}

.deck-loading-skeleton-summary {
  width: min(22rem, 82%);
  height: 0.9rem;
}

.deck-loading-skeleton-description-long {
  width: min(29rem, 92%);
  height: 0.85rem;
}

.deck-loading-skeleton-description-short {
  width: min(20rem, 68%);
  height: 0.85rem;
}

.deck-loading-skeleton-actions {
  width: 2.25rem;
  height: 2.25rem;
}

.deck-loading-skeleton-updated {
  width: 8rem;
  height: 0.8rem;
}

.deck-loading-skeleton-symbol {
  width: 1.5rem;
  height: 1.5rem;
}

.deck-loading-skeleton-compact {
  --deck-skeleton-art-width: min(13rem, 58%);
  --deck-skeleton-content-padding-left: clamp(8rem, 34%, 10rem);
  height: 10.5rem;
}

.deck-loading-skeleton-compact .deck-loading-skeleton-content {
  padding: 0.9rem 1rem 0.85rem var(--deck-skeleton-content-padding-left);
}

@keyframes deck-loading-skeleton-sheen {
  0% {
    transform: translateX(-120%);
  }

  55%,
  100% {
    transform: translateX(120%);
  }
}

@media (max-width: 767px) {
  .deck-loading-skeleton {
    --deck-skeleton-art-width: min(15rem, 70%);
    --deck-skeleton-content-padding-left: clamp(5.4rem, 24%, 7.5rem);
    height: 12rem;
  }

  .deck-loading-skeleton-content {
    padding: 0.95rem 1rem 0.95rem var(--deck-skeleton-content-padding-left);
  }

  .deck-loading-skeleton-actions,
  .deck-loading-skeleton-symbol {
    display: none;
  }
}
</style>
