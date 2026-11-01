<template>
  <!--
    Workbench: the card pool takes every free column (with overlays such as details on top), the collection
    being built sits on the right, and save state and stats run along the bottom.
  -->
  <section class="builder-workspace-layout app-page-layout">
    <section class="builder-workspace-main app-page-layout-main">
      <div class="builder-gallery-scroll app-scrollbar min-h-0">
        <slot />
      </div>
      <!-- Overlays (such as details) cover the pool without unmounting it, so closing returns to it unchanged. -->
      <div
        v-if="$slots.overlay"
        class="builder-workspace-overlay app-scrollbar"
      >
        <slot name="overlay" />
      </div>
    </section>
    <slot name="endAside" />
    <div
      v-if="$slots.status"
      class="builder-workspace-footer"
    >
      <slot name="status" />
    </div>
  </section>
</template>
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
    position: static;
    height: 100%;
    max-height: none;
    min-height: 0;
  }
}
</style>
