<template>
  <AppPageLayout
    columns="one"
    :root-class="
      expanded
        ? 'collection-detail-layout collection-detail-layout-expanded'
        : 'collection-detail-layout'
    "
  >
    <template #aside>
      <div
        class="collection-detail-aside-shell"
        :class="{ 'collection-detail-aside-shell-expanded': expanded }"
      >
        <AppStickyAside
          root-class="collection-detail-primary-aside"
          scroll-class="flex flex-col gap-5 space-y-0"
        >
          <slot name="aside" />
          <template
            v-if="$slots['aside-footer']"
            #footer
          >
            <slot name="aside-footer" />
          </template>
        </AppStickyAside>
        <Transition name="collection-detail-panel">
          <AppStickyAside
            v-if="expanded"
            :id="detailsId"
            root-class="collection-detail-distribution-aside"
            scroll-class="space-y-5"
          >
            <slot name="details" />
            <template
              v-if="$slots['details-footer']"
              #footer
            >
              <slot name="details-footer" />
            </template>
          </AppStickyAside>
        </Transition>
      </div>
    </template>
    <slot />
  </AppPageLayout>
</template>
<script setup lang="ts">
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import AppStickyAside from '@/shared/components/app/AppStickyAside.vue';
defineProps<{ expanded?: boolean; detailsId?: string }>();
</script>
<style scoped>
.collection-detail-aside-shell {
  min-width: 0;
}

.collection-detail-panel-enter-active,
.collection-detail-panel-leave-active {
  overflow: hidden;
  transition:
    max-height 240ms ease,
    opacity 180ms ease,
    transform 240ms ease;
}

.collection-detail-panel-enter-from,
.collection-detail-panel-leave-to {
  max-height: 0;
  opacity: 0;
  transform: translateY(-0.5rem);
}

.collection-detail-panel-enter-to,
.collection-detail-panel-leave-from {
  max-height: 100rem;
  opacity: 1;
  transform: translateY(0);
}

@media (min-width: 1280px) {
  .collection-detail-layout {
    grid-template-columns: 22.5rem minmax(0, 1fr);
    transition: grid-template-columns 240ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  .collection-detail-layout-expanded {
    grid-template-columns: 47.5rem minmax(0, 1fr);
  }

  .collection-detail-aside-shell {
    display: grid;
    grid-template-columns: 22.5rem 0;
    overflow: clip;
    transition: grid-template-columns 240ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  .collection-detail-aside-shell-expanded {
    grid-template-columns: 22.5rem 25rem;
  }

  :deep(.collection-detail-primary-aside) {
    z-index: 1;
  }

  :deep(.collection-detail-distribution-aside) {
    min-width: 0;
    overflow: hidden;
    border-right-width: 1px;
    border-left-width: 1px;
  }

  .collection-detail-panel-enter-active,
  .collection-detail-panel-leave-active {
    max-height: none;
    transition:
      opacity 180ms ease,
      transform 240ms ease;
  }

  .collection-detail-panel-enter-from,
  .collection-detail-panel-leave-to {
    max-height: none;
    transform: translateX(-0.75rem);
  }
}

@media (prefers-reduced-motion: reduce) {
  .collection-detail-layout,
  .collection-detail-aside-shell,
  .collection-detail-panel-enter-active,
  .collection-detail-panel-leave-active {
    transition-duration: 0.01ms !important;
  }
}
</style>
