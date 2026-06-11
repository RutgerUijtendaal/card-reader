<template>
  <div
    class="theme-hotkeys-panel"
    :class="compact ? 'items-center px-2 py-3 text-center' : ''"
  >
    <template v-if="compact">
      <Keyboard class="h-4 w-4" />
      <span class="text-[11px] font-semibold uppercase tracking-[0.18em]">Hotkeys</span>
      <span class="text-[11px]">/</span>
      <span class="text-[11px]">Alt 1-4</span>
      <span class="text-[11px]">Alt Wheel</span>
      <span
        v-if="auth.authenticated"
        class="text-[11px]"
      >
        N N
      </span>
    </template>

    <template v-else>
      <div class="flex items-center gap-2">
        <span class="theme-hotkeys-icon-wrap">
          <Keyboard class="h-4 w-4" />
        </span>
        <div class="min-w-0">
          <p class="text-sm font-semibold">
            Hotkeys
          </p>
          <p class="text-xs opacity-75">
            Search and quick actions
          </p>
        </div>
      </div>

      <div class="space-y-2 text-sm">
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Search</span>
          <span class="theme-hotkey-chip">/</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Hover Mode</span>
          <span class="theme-hotkey-chip">Alt+1/2/3/4</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Hover Size</span>
          <span class="theme-hotkey-chip">Alt+Wheel</span>
        </div>
        <div
          v-if="auth.authenticated"
          class="flex items-center justify-between gap-3"
        >
          <span class="opacity-80">New Deck</span>
          <span class="inline-flex items-center gap-1">
            <span class="theme-hotkey-chip">N</span>
            <span class="theme-hotkey-chip">N</span>
          </span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { Keyboard } from 'lucide-vue-next';
import { useAuthStore } from '@/modules/auth/authStore';

withDefaults(
  defineProps<{
    compact?: boolean;
  }>(),
  {
    compact: false,
  },
);

const auth = useAuthStore();
</script>
