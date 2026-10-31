<template>
  <AppPageLayout
    columns="three"
    root-class="builder-workspace-layout"
    main-class="builder-workspace-main"
  >
    <template #aside>
      <slot name="aside" />
    </template>
    <div class="builder-gallery-column flex min-w-0 flex-col gap-4">
      <slot name="status" />
      <div class="builder-gallery-scroll app-scrollbar min-h-0 flex-1">
        <slot />
      </div>
    </div>
    <template #endAside>
      <slot name="endAside" />
    </template>
  </AppPageLayout>
</template>
<script setup lang="ts">
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
</script>
<style scoped>
.builder-workspace-layout,
:deep(.builder-workspace-main) {
  padding-top: 0;
  padding-right: 0;
  padding-left: 0;
}
@media (min-width: 1280px) {
  .builder-workspace-layout {
    height: calc(100dvh - var(--app-page-header-height, 0px));
    min-height: 0;
    overflow: hidden;
  }
  :deep(.builder-workspace-main),
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
