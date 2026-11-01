<template>
  <nav
    class="theme-tablist flex-nowrap"
    :aria-label="label"
  >
    <RouterLink
      v-for="tab in tabs"
      :key="tab.label"
      class="theme-tab min-w-0 px-4"
      :class="{ 'theme-tab-active': tab.active }"
      :to="tab.to"
      :aria-current="tab.active ? 'page' : undefined"
    >
      <component
        :is="tab.icon"
        v-if="tab.icon"
        class="h-4 w-4 shrink-0"
        aria-hidden="true"
      />
      <span class="truncate">{{ tab.label }}</span>
    </RouterLink>
  </nav>
</template>

<script setup lang="ts">
import type { Component } from 'vue';
import { RouterLink, type RouteLocationRaw } from 'vue-router';

export type AppScopeTab = {
  label: string;
  to: RouteLocationRaw;
  active: boolean;
  icon?: Component;
};

defineProps<{
  /** Accessible name for the scope switcher, such as "Deck library". */
  label: string;
  tabs: AppScopeTab[];
}>();
</script>
