<template>
  <nav
    class="theme-toggle-shell"
    :aria-label="label"
  >
    <RouterLink
      v-for="option in options"
      :key="option.label"
      class="theme-toggle-option whitespace-nowrap"
      :class="{ 'theme-toggle-option-active': option.active }"
      :to="option.to"
      :aria-current="option.active ? 'page' : undefined"
    >
      {{ option.label }}
    </RouterLink>
  </nav>
</template>

<script setup lang="ts">
import { RouterLink, type RouteLocationRaw } from 'vue-router';

/** One collection seen through different scopes, such as public records or your own. */
export type AppScopeOption = {
  label: string;
  to: RouteLocationRaw;
  active: boolean;
};

defineProps<{
  /** Accessible name for the scope switcher, such as "Deck library". */
  label: string;
  options: AppScopeOption[];
}>();
</script>
