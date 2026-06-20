<template>
  <div
    class="theme-hotkeys-panel"
    :class="compact ? 'items-center px-2 py-3 text-center' : ''"
  >
    <template v-if="compact">
      <Keyboard class="h-4 w-4" />
      <span class="text-[11px] font-semibold uppercase tracking-[0.18em]">Hotkeys</span>
      <template v-if="isPlaytesterRoute">
        <span class="text-[11px]">N / U / D / O</span>
        <span class="text-[11px]">T / F / G / R</span>
        <span class="text-[11px]">Del</span>
        <span class="text-[11px]">Ctrl Z/Y</span>
        <span class="text-[11px]">Ctrl C/V</span>
        <span class="text-[11px]">Middle Mouse</span>
        <span class="text-[11px]">Alt Wheel</span>
      </template>
      <template v-else>
        <span class="text-[11px]">/</span>
        <span class="text-[11px]">Alt 1-5</span>
        <span class="text-[11px]">Alt Wheel</span>
      </template>
      <span
        v-if="!isPlaytesterRoute && auth.authenticated"
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
            {{ isPlaytesterRoute ? 'Playtester actions' : 'Search and quick actions' }}
          </p>
        </div>
      </div>

      <div
        v-if="isPlaytesterRoute"
        class="space-y-2 text-sm"
      >
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Next turn</span>
          <span class="theme-hotkey-chip">N</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Untap all</span>
          <span class="theme-hotkey-chip">U</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Draw</span>
          <span class="theme-hotkey-chip">D</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Library</span>
          <span class="theme-hotkey-chip">O</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Tap</span>
          <span class="theme-hotkey-chip">T</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Flip</span>
          <span class="theme-hotkey-chip">F</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Group</span>
          <span class="theme-hotkey-chip">G</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Shuffle</span>
          <span class="theme-hotkey-chip">R</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Delete</span>
          <span class="theme-hotkey-chip">Del</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Undo</span>
          <span class="theme-hotkey-chip">Ctrl+Z</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Redo</span>
          <span class="inline-flex items-center gap-1">
            <span class="theme-hotkey-chip">Ctrl+Shift+Z</span>
            <span class="theme-hotkey-chip">Ctrl+Y</span>
          </span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Copy/Paste</span>
          <span class="inline-flex items-center gap-1">
            <span class="theme-hotkey-chip">Ctrl+C</span>
            <span class="theme-hotkey-chip">Ctrl+V</span>
          </span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Zoom card</span>
          <span class="theme-hotkey-chip">Middle Mouse</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Scale</span>
          <span class="theme-hotkey-chip">Alt+Wheel</span>
        </div>
      </div>

      <div
        v-else
        class="space-y-2 text-sm"
      >
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Search</span>
          <span class="theme-hotkey-chip">/</span>
        </div>
        <div class="flex items-center justify-between gap-3">
          <span class="opacity-80">Hover Mode</span>
          <span class="theme-hotkey-chip">Alt+1/2/3/4/5</span>
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
import { computed } from 'vue';
import { Keyboard } from 'lucide-vue-next';
import { useRoute } from 'vue-router';
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
const route = useRoute();
const isPlaytesterRoute = computed(() => route.path === '/playtester' || route.path.startsWith('/playtester/'));
</script>
