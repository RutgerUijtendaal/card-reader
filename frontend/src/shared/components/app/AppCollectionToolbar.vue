<template>
  <div class="flex w-full flex-wrap items-center gap-x-2 gap-y-2">
    <!-- The search gives up width (down to 18rem) before anything wraps, and grows back when there is room. -->
    <div class="mr-1 w-full sm:w-auto sm:max-w-[26rem] sm:flex-[1_1_18rem]">
      <slot name="search" />
    </div>
    <!-- `contents` lets each filter chip wrap on its own instead of moving the whole group. -->
    <div
      v-if="$slots.filters"
      class="contents"
    >
      <slot name="filters" />
    </div>
    <div
      v-if="$slots.actions"
      class="ml-auto flex flex-wrap items-center gap-2"
    >
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * One toolbar row for browse pages and builders: search and count, then filters, then page
 * options on the right. Filter items flow as individual row items and wrap only when the row
 * runs out of room.
 */
defineSlots<{
  search(): unknown;
  filters?(): unknown;
  actions?(): unknown;
}>();
</script>
