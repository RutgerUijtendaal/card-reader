<template>
  <!-- Workbench: the card pool takes every free column; filters live in the page header bar. -->
  <section class="builder-workspace-layout app-page-layout">
    <section class="builder-workspace-main app-page-layout-main">
      <div class="builder-gallery-column flex min-w-0 flex-col gap-4">
        <slot name="status" />
        <div class="builder-gallery-scroll app-scrollbar min-h-0 flex-1">
          <slot />
        </div>
      </div>
    </section>
    <slot name="endAside" />
  </section>
</template>
<style scoped>
.builder-workspace-layout {
  grid-template-columns: minmax(0, 1fr);
  padding-top: 0;
  padding-right: 0;
}

.builder-workspace-main {
  padding-top: 0;
  padding-right: 0;
  padding-left: 0;
}

@media (min-width: 1280px) {
  .builder-workspace-layout {
    grid-template-columns: minmax(0, 1fr) 24rem;
    height: calc(100dvh - var(--app-page-header-height, 0px));
    min-height: 0;
    overflow: hidden;
  }

  .builder-workspace-main,
  .builder-gallery-column {
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .builder-gallery-scroll {
    overflow-y: auto;
    overscroll-behavior: contain;
  }
}
</style>
