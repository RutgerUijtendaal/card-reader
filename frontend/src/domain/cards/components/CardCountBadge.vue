<template>
  <span
    v-if="!hideWhenZero || quantity > 0"
    class="theme-pill theme-pill-accent pointer-events-auto text-xs"
  >
    x{{ quantity }}
  </span>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    quantity: number;
    hideWhenZero?: boolean;
  }>(),
  {
    hideWhenZero: false,
  },
);
</script>
