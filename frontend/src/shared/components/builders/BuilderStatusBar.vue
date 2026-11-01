<template>
  <section
    class="builder-status-bar flex shrink-0 flex-col gap-3 px-4 py-2.5 lg:flex-row lg:items-center lg:justify-between"
  >
    <slot />
  </section>
</template>
<style scoped>
/* The workbench's bottom bar: save state on the left, collection stats on the right. */
.builder-status-bar {
  border-top: 1px solid var(--color-border);
  background: color-mix(in srgb, var(--table-canvas-deep) 88%, var(--color-surface-strong));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
</style>
