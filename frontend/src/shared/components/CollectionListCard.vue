<template>
  <article
    :class="cardClass"
    :data-navigation-target="navigationTarget"
    :role="to ? 'link' : undefined"
    :tabindex="to ? 0 : undefined"
    @click="navigate"
    @keydown.enter.prevent="navigate"
    @keydown.space.prevent="navigate"
  >
    <div class="collection-tile-art">
      <img
        v-if="imageUrl"
        :src="imageUrl"
        :alt="imageAlt"
        class="collection-tile-art-image"
        loading="lazy"
      >
      <div
        v-else
        class="collection-tile-art-fallback"
        aria-hidden="true"
      />
      <div
        class="collection-tile-art-scrim"
        aria-hidden="true"
      />
      <div
        v-if="$slots.badge"
        class="collection-tile-art-badge"
      >
        <slot name="badge" />
      </div>
      <div
        v-if="$slots.actions"
        class="collection-tile-art-actions"
        data-card-click-ignore="true"
      >
        <slot name="actions" />
      </div>
      <div
        v-if="$slots['art-corner']"
        class="collection-tile-art-corner"
      >
        <slot name="art-corner" />
      </div>
    </div>

    <div class="collection-tile-body">
      <div class="flex min-w-0 items-start gap-2">
        <h3 class="collection-tile-title theme-section-title theme-display min-w-0 flex-1">
          {{ title }}
        </h3>
        <slot name="title-extra" />
      </div>
      <p
        v-if="description"
        class="collection-tile-description theme-section-muted text-sm"
      >
        {{ description }}
      </p>
      <div
        v-if="$slots.tags"
        class="collection-tile-tags"
      >
        <slot name="tags" />
      </div>
      <div class="collection-tile-footer theme-section-muted text-xs">
        <slot name="footer" />
      </div>
    </div>
  </article>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { useRouter, type RouteLocationRaw } from 'vue-router';

/**
 * A deck or Encounter tile: cover art cropped to the hero or boss with status and actions laid
 * over it, then the title, an optional description, tags, and a one-line footer.
 */
const props = defineProps<{
  title: string;
  description?: string | null;
  imageUrl?: string | null;
  imageAlt?: string;
  to?: RouteLocationRaw;
  variant?: string;
}>();
const router = useRouter();
const navigationTarget = computed(() => (props.to ? router.resolve(props.to).fullPath : undefined));
const cardClass = computed(() => [
  'collection-tile page-card',
  props.variant ? `collection-tile-${props.variant}` : '',
  props.to
    ? 'cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--table-canvas)]'
    : '',
]);
const navigate = (event: MouseEvent | KeyboardEvent): void => {
  if (!props.to) return;
  if (
    event.target instanceof Element &&
    event.target.closest(
      'a, button, input, select, textarea, summary, details, [role="button"], [data-card-click-ignore="true"]',
    )
  )
    return;
  void router.push(props.to);
};
</script>
<style scoped>
.collection-tile {
  display: flex;
  min-width: 0;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
  transition:
    border-color 180ms ease,
    transform 180ms ease;
}

.collection-tile:hover {
  border-color: color-mix(in srgb, var(--accent) 45%, var(--color-border));
}

/* The cover keeps close to the shape of the printed art window, trimmed a little at the top and
   bottom so neither the name banner nor the type line shows, rather than stretching the art. */
.collection-tile-art {
  position: relative;
  aspect-ratio: 3 / 2;
  flex-shrink: 0;
  overflow: hidden;
  background: var(--color-surface-soft);
}

/* Show only the art window: the image is widened past the side borders and lifted past the
   name banner. Percentage margins resolve against the tile width, matching the card's shape. */
.collection-tile-art-image {
  display: block;
  width: 114%;
  max-width: none;
  height: auto;
  margin-top: -14%;
  margin-left: -7%;
}

.collection-tile-art-fallback {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top left, color-mix(in srgb, var(--accent) 30%, transparent), transparent 55%),
    linear-gradient(140deg, var(--color-surface-strong), var(--color-surface-soft));
}

.collection-tile-art-scrim {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(
    to bottom,
    rgb(4 6 18 / 0.35) 0%,
    transparent 30%,
    transparent 62%,
    rgb(4 6 18 / 0.55) 100%
  );
}

.collection-tile-art-badge {
  position: absolute;
  top: 0.625rem;
  left: 0.625rem;
  display: flex;
  max-width: calc(100% - 4rem);
  flex-wrap: wrap;
  gap: 0.375rem;
}

.collection-tile-art-actions {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  display: flex;
  gap: 0.375rem;
}

.collection-tile-art-corner {
  position: absolute;
  right: 0.625rem;
  bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.collection-tile-body {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.875rem 1rem 0.875rem;
}

.collection-tile-title {
  display: -webkit-box;
  overflow: hidden;
  font-size: 1.125rem;
  line-height: 1.3;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.collection-tile-description {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.collection-tile-footer {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.5rem;
  margin-top: auto;
  padding-top: 0.25rem;
  white-space: nowrap;
}

:deep(.collection-tile-footer-items) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

:deep(.collection-tile-footer-item + .collection-tile-footer-item)::before {
  content: '·';
  margin-right: 0.5rem;
  opacity: 0.7;
}

:deep(.collection-tile-footer-end) {
  flex-shrink: 0;
  margin-left: auto;
}
</style>
