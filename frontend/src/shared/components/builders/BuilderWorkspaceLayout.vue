<template>
  <!--
    Workbench: the card pool takes every free column (with overlays such as details on top), the collection
    being built sits on the right, and save state and stats run along the bottom.
  -->
  <section class="builder-workspace-layout app-page-layout">
    <slot name="endAside" />
    <section class="builder-workspace-main app-page-layout-main">
      <div
        class="builder-gallery-scroll app-scrollbar min-h-0"
        :inert="$slots.overlay ? true : undefined"
      >
        <slot />
      </div>
      <!-- Overlays (such as details) cover the pool without unmounting it, so closing returns to it unchanged. -->
      <div
        v-if="$slots.overlay"
        ref="overlayRef"
        class="builder-workspace-overlay app-scrollbar"
        tabindex="-1"
      >
        <slot name="overlay" />
      </div>
    </section>
    <div
      v-if="$slots.status"
      class="builder-workspace-footer"
    >
      <slot name="status" />
    </div>
  </section>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue';

const overlayRef = ref<HTMLElement | null>(null);
let previousFocus: HTMLElement | null = null;

watch(
  overlayRef,
  (overlay) => {
    if (overlay) {
      previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      const control = overlay.querySelector<HTMLElement>(
        'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)',
      );
      (control ?? overlay).focus();
    } else {
      // A panel tab may have closed Details; keep focus there instead of stealing it back.
      if (document.activeElement === document.body && previousFocus?.isConnected) {
        previousFocus.focus();
      }
      previousFocus = null;
    }
  },
  { flush: 'post' },
);
</script>
<style scoped>
.builder-workspace-layout {
  grid-template-columns: minmax(0, 1fr);
  padding-top: 0;
  padding-right: 0;
  padding-bottom: 0;
  row-gap: 0;
}

.builder-workspace-main {
  position: relative;
  padding-top: 0;
  padding-right: 0;
  padding-left: 0;
}

.builder-workspace-overlay {
  position: absolute;
  inset: 0;
  z-index: 25;
  overflow-y: auto;
  overscroll-behavior: contain;
  border-right: 1px solid var(--color-border);
  background: var(--table-canvas);
}

.builder-workspace-footer {
  position: sticky;
  bottom: 0;
  z-index: 20;
  grid-column: 1 / -1;
}

@media (min-width: 1280px) {
  .builder-workspace-layout {
    grid-template-columns: minmax(0, 1fr) 24rem;
    grid-template-rows: minmax(0, 1fr) auto;
    align-items: stretch;
    height: calc(100dvh - var(--app-page-header-height, 0px));
    min-height: 0;
    overflow: hidden;
  }

  .builder-workspace-main {
    grid-column: 1;
    grid-row: 1;
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .builder-gallery-scroll {
    height: 100%;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  /* The right column fills its grid row so the bottom bar never covers its list. */
  .builder-workspace-layout > :deep(.app-sticky-aside) {
    grid-column: 2;
    grid-row: 1;
    position: static;
    height: 100%;
    max-height: none;
    min-height: 0;
  }
}
</style>
