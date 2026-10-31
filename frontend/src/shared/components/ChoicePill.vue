<template>
  <button
    class="theme-pill text-sm"
    :class="selected ? 'theme-pill-accent' : 'theme-pill-neutral'"
    type="button"
    :aria-pressed="selected"
  >
    <slot />
  </button>
</template>
<script setup lang="ts">
defineProps<{ selected: boolean }>();
</script>
