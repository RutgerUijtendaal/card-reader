<template>
  <div class="flex w-full flex-wrap items-center gap-x-3 gap-y-2">
    <div class="w-full shrink-0 sm:w-[26rem]">
      <slot name="search" />
    </div>
    <div
      v-if="$slots.filters"
      class="flex min-w-0 flex-wrap items-center gap-2"
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
 * One toolbar row for browse pages: search and count, then filters, then page options on the
 * right. Items wrap only when the row runs out of room.
 */
defineSlots<{
  search(): unknown;
  filters?(): unknown;
  actions?(): unknown;
}>();
</script>
