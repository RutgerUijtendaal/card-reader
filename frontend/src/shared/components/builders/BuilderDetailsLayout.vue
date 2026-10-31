<template>
  <AppPageLayout
    columns="sidebar"
    root-class="builder-details-layout"
    main-class="builder-details-main"
  >
    <template #aside>
      <slot name="aside" />
    </template>
    <slot name="status" />
    <div class="builder-details-content">
      <slot />
    </div>
  </AppPageLayout>
</template>
<script setup lang="ts">
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
</script>
<style scoped>
.builder-details-layout,
:deep(.builder-details-main) {
  padding: 0;
}
.builder-details-content {
  padding: var(--app-page-y-inset) var(--app-page-x-inset);
}
</style>
