<template>
  <div
    class="collection-tile-skeleton page-card"
    :class="{ 'collection-tile-skeleton-static': !animated }"
    aria-hidden="true"
  >
    <div class="collection-tile-skeleton-art" />
    <div class="collection-tile-skeleton-body">
      <span class="collection-tile-skeleton-line w-3/4" />
      <span class="collection-tile-skeleton-line w-full opacity-70" />
      <span class="collection-tile-skeleton-line w-2/3 opacity-70" />
      <span class="collection-tile-skeleton-line mt-auto w-1/2" />
    </div>
  </div>
</template>

<script setup lang="ts">
/** The loading placeholder for a deck or Encounter tile, matching its art and body proportions. */
withDefaults(defineProps<{ animated?: boolean }>(), { animated: true });
</script>

<style scoped>
.collection-tile-skeleton {
  position: relative;
  display: flex;
  min-width: 0;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.collection-tile-skeleton::after {
  content: '';
  position: absolute;
  inset: 0;
  transform: translateX(-120%);
  background: linear-gradient(
    90deg,
    transparent 0%,
    color-mix(in srgb, var(--color-text) 8%, transparent) 50%,
    transparent 100%
  );
  animation: collection-tile-skeleton-sheen 1.6s ease-in-out infinite;
  pointer-events: none;
}

.collection-tile-skeleton-static::after {
  display: none;
}

.collection-tile-skeleton-art {
  aspect-ratio: 3 / 2;
  background: linear-gradient(
    135deg,
    var(--color-surface-strong),
    color-mix(in srgb, var(--color-surface-soft) 80%, var(--color-border))
  );
}

.collection-tile-skeleton-body {
  display: flex;
  min-height: 8rem;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.875rem 1rem;
}

.collection-tile-skeleton-line {
  display: block;
  height: 0.75rem;
  border-radius: 9999px;
  background: color-mix(in srgb, var(--color-border) 70%, transparent);
}

@keyframes collection-tile-skeleton-sheen {
  100% {
    transform: translateX(120%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .collection-tile-skeleton::after {
    animation: none;
  }
}
</style>
