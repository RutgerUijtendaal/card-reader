<template>
  <div class="flex flex-wrap items-center gap-3">
    <CardSortMenu
      :sort="sortSurface.effectiveSort.value"
      :default-sort="sortSurface.defaultSort.value"
      :override-active="sortSurface.overrideSort.value !== null"
      allow-default-option
      @update:sort="sortSurface.setOverrideSort"
      @reset="sortSurface.clearOverrideSort"
    />
    <GalleryOptionsMenu
      :hover-mode="hoverSurface.effectiveHoverMode.value"
      :default-hover-mode="hoverSurface.defaultHoverMode.value"
      :hover-mode-override-active="hoverSurface.overrideHoverMode.value !== null"
      allow-hover-mode-default-option
      :card-scale="cardScale"
      :show-card-groups="false"
      :show-card-groups-control="false"
      :group-by-type="groupByType"
      show-group-by-type-control
      @update:hover-mode="hoverSurface.setOverrideHoverMode"
      @reset:hover-mode="hoverSurface.clearOverrideHoverMode"
      @update:card-scale="cardScale = $event"
      @update:group-by-type="groupByType = $event"
    />
  </div>
</template>
<script setup lang="ts">
import CardSortMenu from '@/domain/cards/components/CardSortMenu.vue';
import GalleryOptionsMenu from '@/domain/cards/components/GalleryOptionsMenu.vue';
import type { useCardSortSurface } from '@/domain/cards/composables/useCardSortPreferences';
import type { useHoverModeSurface } from '@/domain/cards/composables/useHoverModePreferences';
defineProps<{
  sortSurface: ReturnType<typeof useCardSortSurface>;
  hoverSurface: ReturnType<typeof useHoverModeSurface>;
}>();
const cardScale = defineModel<number>('cardScale', { required: true });
const groupByType = defineModel<boolean>('groupByType', { required: true });
</script>
