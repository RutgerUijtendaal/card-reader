<template>
  <div
    class="app-empty-state flex flex-col items-center justify-center gap-3 px-6 py-14 text-center"
    role="status"
  >
    <span
      v-if="icon"
      class="app-empty-state-icon inline-flex h-12 w-12 items-center justify-center rounded-full"
      aria-hidden="true"
    >
      <component
        :is="icon"
        class="h-5 w-5"
      />
    </span>
    <div class="max-w-md space-y-1">
      <p class="theme-section-title theme-display text-lg">
        {{ title }}
      </p>
      <p
        v-if="message"
        class="theme-section-muted text-sm leading-6"
      >
        {{ message }}
      </p>
    </div>
    <div
      v-if="$slots.default"
      class="mt-1 flex flex-wrap items-center justify-center gap-2"
    >
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue';

withDefaults(
  defineProps<{
    title: string;
    message?: string;
    icon?: Component;
  }>(),
  {
    message: '',
    icon: undefined,
  },
);
</script>

<style scoped>
.app-empty-state {
  border: 1px dashed var(--color-border-strong);
  border-radius: 0.75rem;
}

.app-empty-state-icon {
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  color: var(--accent);
}
</style>
