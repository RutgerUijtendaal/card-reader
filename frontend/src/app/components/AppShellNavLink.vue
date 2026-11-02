<template>
  <RouterLink
    class="nav-link relative"
    :class="[collapsed ? 'justify-center px-0' : '', { 'router-link-active': alsoActive }]"
    :to="item.to"
    :title="collapsed ? item.label : undefined"
    :aria-label="collapsed ? item.label : undefined"
    @click="$emit('navigate')"
  >
    <component
      :is="item.icon"
      class="h-[1.125rem] w-[1.125rem] shrink-0"
      :data-card-pool-icon="item.cardPool"
    />
    <span
      v-if="!collapsed"
      class="min-w-0 truncate"
    >{{ item.label }}</span>
    <span
      v-if="collapsed && hasBadge"
      class="nav-indicator-dot"
      aria-hidden="true"
    />
    <span
      v-if="!collapsed && hasBadge"
      class="nav-badge theme-pill theme-pill-success ml-auto text-[11px] font-semibold"
    >
      {{ item.badgeCount }}
    </span>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Component } from 'vue';
import { RouterLink } from 'vue-router';
import type { RouteLocationRaw } from 'vue-router';
import type { CardPool } from '@/domain/cards/cardPools';

export type AppShellNavItem = {
  label: string;
  to: RouteLocationRaw;
  icon: Component;
  cardPool?: CardPool;
  badgeCount?: number;
};

const props = withDefaults(
  defineProps<{
    item: AppShellNavItem;
    collapsed?: boolean;
    /** Highlights the link on routes RouterLink does not match itself, such as a library's Mine scope. */
    alsoActive?: boolean;
  }>(),
  {
    collapsed: false,
    alsoActive: false,
  },
);

defineEmits<{ navigate: [] }>();

const hasBadge = computed(() => (props.item.badgeCount ?? 0) > 0);
</script>

<style scoped>
.nav-badge {
  height: 1.25rem;
  min-width: 1.25rem;
  justify-content: center;
  padding: 0 0.375rem;
  line-height: 1;
}

.nav-indicator-dot {
  position: absolute;
  top: 0.5rem;
  right: 0.75rem;
  width: 0.55rem;
  height: 0.55rem;
  border: 2px solid rgba(15, 23, 42, 0.92);
  border-radius: 9999px;
  background: var(--color-pill-success-text);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-pill-success-border) 34%, transparent);
}
</style>
