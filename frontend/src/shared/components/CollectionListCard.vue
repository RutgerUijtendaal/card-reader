<template>
  <div class="collection-list-card-shell min-w-0">
    <div
      :class="cardClass"
      :data-navigation-target="navigationTarget"
      :role="to ? 'link' : undefined"
      :tabindex="to ? 0 : undefined"
      @click="navigate"
      @keydown.enter.prevent="navigate"
      @keydown.space.prevent="navigate"
    >
      <div class="collection-list-card-art">
        <img
          v-if="imageUrl"
          :src="imageUrl"
          :alt="imageAlt"
          class="collection-list-card-art-image"
        >
        <div
          v-else
          class="collection-list-card-art-fallback"
          aria-hidden="true"
        />
      </div>
      <div class="collection-list-card-content">
        <div class="flex items-start gap-4">
          <div class="collection-list-card-main min-w-0 flex-1">
            <div
              class="collection-list-card-title-row flex min-w-0 items-center justify-between gap-3"
            >
              <div class="flex min-w-0 flex-1 items-center gap-2">
                <h3 class="theme-section-title min-w-0 flex-1 truncate text-xl font-semibold">
                  {{ title }}
                </h3>
                <slot name="title-extra" />
              </div>
              <slot name="badge" />
            </div>
            <p
              class="collection-list-card-description text-sm"
              :class="description ? 'theme-section-title' : 'theme-section-muted'"
            >
              {{ description || 'No description available.' }}
            </p>
          </div>
          <div
            v-if="$slots.actions"
            class="shrink-0"
            data-card-click-ignore="true"
          >
            <slot name="actions" />
          </div>
        </div>
        <div class="collection-list-card-tags-region">
          <slot name="tags" />
        </div>
        <div class="collection-list-card-footer flex flex-wrap items-center justify-between gap-3">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { useRouter, type RouteLocationRaw } from 'vue-router';
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
  'collection-list-card-surface page-card',
  props.variant ? `collection-list-card-${props.variant}` : '',
  props.to
    ? 'cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--theme-surface)]'
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
.collection-list-card-surface {
  --collection-card-art-text-gap: 1.5rem;
  --collection-card-art-position: 23% 7%;
  --collection-card-art-scale: 1.265;
  --collection-card-art-hover-scale: 1.27;
  --collection-card-art-hover-shift-x: 0.2rem;
  --collection-card-content-padding-left: 20rem;
  --collection-card-art-width: calc(
    var(--collection-card-content-padding-left) - var(--collection-card-art-text-gap)
  );
  position: relative;
  min-height: 14.5rem;
  overflow: hidden;
  padding: 0;
}

.collection-list-card-art {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--collection-card-art-width);
  overflow: hidden;
  border: 1px solid var(--color-border-strong);
  border-radius: 0.75rem 0 0 0.75rem;
  background:
    radial-gradient(circle at top left, rgba(148, 163, 184, 0.26), transparent 55%),
    linear-gradient(135deg, rgba(30, 41, 59, 0.96), rgba(15, 23, 42, 0.92));
}

.collection-list-card-art-image {
  height: 100%;
  width: 100%;
  object-fit: cover;
  object-position: var(--collection-card-art-position);
  transform: scale(var(--collection-card-art-scale));
  transition: transform 240ms ease;
}

.collection-list-card-surface:hover .collection-list-card-art-image,
.collection-list-card-surface:focus-within .collection-list-card-art-image {
  transform: scale(var(--collection-card-art-hover-scale))
    translateX(var(--collection-card-art-hover-shift-x));
}

.collection-list-card-art-fallback {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at top left, rgba(244, 114, 182, 0.32), transparent 45%),
    radial-gradient(circle at bottom left, rgba(59, 130, 246, 0.24), transparent 48%),
    linear-gradient(140deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.96));
}

.collection-list-card-content {
  position: relative;
  z-index: 1;
  display: flex;
  min-height: inherit;
  min-width: 0;
  flex-direction: column;
  padding: 1.1rem 1.2rem 1.1rem var(--collection-card-content-padding-left);
}

.collection-list-card-description {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 0.75rem;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.collection-list-card-main {
  display: flex;
  flex-direction: column;
}

.collection-list-card-tags-region {
  display: flex;
  flex: 1;
  align-items: center;
  padding-block: 0.75rem;
}

:deep(.collection-list-card-tags) {
  align-items: center;
}

:deep(.collection-list-card-footer-meta) {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  align-items: center;
  row-gap: 0.35rem;
}

:deep(.collection-list-card-footer-meta-item) {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  white-space: nowrap;
}

:deep(.collection-list-card-footer-meta-item + .collection-list-card-footer-meta-item) {
  margin-left: 0.75rem;
  border-left: 1px solid var(--color-border-strong);
  padding-left: 0.75rem;
}

@media (max-width: 767px) {
  .collection-list-card-surface {
    --collection-card-art-text-gap: 1rem;
    --collection-card-content-padding-left: clamp(5.4rem, 24%, 7.5rem);
    min-height: 12rem;
  }

  .collection-list-card-content {
    padding: 0.95rem 1rem 0.95rem var(--collection-card-content-padding-left);
  }
}
</style>
