<template>
  <section
    class="builder-status-bar flex shrink-0 flex-col gap-4 px-4 py-3 lg:flex-row lg:items-center lg:justify-between"
  >
    <slot />
  </section>
</template>
<style scoped>
.builder-status-bar {
  position: sticky;
  top: 0;
  z-index: 20;
  background: var(--color-surface-strong);
}
.builder-status-bar::after {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 1px;
  content: '';
  background: var(--color-border);
}
</style>
