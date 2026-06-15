<template>
  <div class="flex h-screen overflow-hidden">
    <aside
      v-if="isDesktop"
      class="h-full shrink-0 transition-[width] duration-200"
      :class="isSidebarCollapsed ? 'w-[5.75rem]' : 'w-[17rem]'"
    >
      <AppShellNav
        :collapsed="isSidebarCollapsed"
        :can-collapse="true"
        @toggle-collapse="isSidebarCollapsed = !isSidebarCollapsed"
      />
    </aside>

    <div
      class="flex min-w-0 flex-1 flex-col overflow-hidden"
      :style="{ '--app-page-header-height': pageHeaderHeight }"
    >
      <div class="theme-panel-shell m-3 flex items-center justify-between rounded-2xl px-4 py-3 lg:hidden">
        <button
          type="button"
          class="theme-card-frame-muted theme-icon-button theme-section-title inline-flex h-10 w-10 items-center justify-center rounded-xl"
          aria-label="Open navigation"
          @click="mobileNavOpen = true"
        >
          <Menu class="h-5 w-5" />
        </button>

        <RouterLink
          class="flex items-center gap-3"
          to="/cards"
        >
          <span class="flex h-11 w-11 items-center justify-center rounded-xl">
            <img
              :src="cardLogoUrl"
              alt=""
              class="h-full w-full object-contain"
            >
          </span>
          <span class="text-sm font-semibold">Maity's Card Game</span>
        </RouterLink>

        <div class="h-10 w-10" />
      </div>

      <div
        id="app-page-header-outlet"
        ref="pageHeaderOutletRef"
        class="shrink-0"
      />

      <main
        ref="scrollContainerRef"
        class="app-main-scroll app-scrollbar min-h-0 flex-1 overflow-y-auto"
      >
        <RouterView />
      </main>
    </div>
  </div>

  <Teleport to="body">
    <div
      v-if="mobileNavOpen && !isDesktop"
      class="fixed inset-0 z-50 lg:hidden"
    >
      <button
        type="button"
        class="theme-overlay absolute inset-0"
        aria-label="Close navigation"
        @click="mobileNavOpen = false"
      />

      <aside class="absolute inset-y-0 left-0 w-[19rem] max-w-[85vw]">
        <AppShellNav
          mobile
          @close-mobile="mobileNavOpen = false"
        />
      </aside>
    </div>
  </Teleport>

  <Toaster
    rich-colors
    position="bottom-right"
    close-button
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useEventListener, useLocalStorage, useMediaQuery, useResizeObserver } from '@vueuse/core';
import { Menu } from 'lucide-vue-next';
import { Toaster } from 'vue-sonner';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import AppShellNav from '@/components/app/AppShellNav.vue';
import { useGlobalNavigationHotkeys, useHoverModeHotkeys, usePrimarySearchHotkeys } from '@/composables/useHotkeys';
import { provideScrollContainer } from '@/composables/useScrollContainer';
import { useAuthStore } from '@/modules/auth/authStore';
import { buildContextualNewDeckEditorLocation } from '@/composables/decks/deckRouteState';
import type { HoverMode } from '@/composables/card-gallery/hoverMode';
import {
  handleHoverPreviewScaleWheel,
  resolveHoverModeSurfacePath,
  useHoverModePreferences,
  type HoverModeSurface,
} from '@/composables/useHoverModePreferences';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const hoverModePreferences = useHoverModePreferences();
const scrollContainerRef = ref<HTMLElement | null>(null);
const pageHeaderOutletRef = ref<HTMLElement | null>(null);
const pageHeaderHeight = ref('0px');
const isDesktop = useMediaQuery('(min-width: 1024px)');
const mobileNavOpen = ref(false);
const isSidebarCollapsed = useLocalStorage('card-reader.sidebar-collapsed', false, {
  writeDefaults: true,
});
const cardLogoUrl = `${import.meta.env.BASE_URL}card_logo_transparent.webp`;
const isActivePlaytesterRoute = computed(() => route.path === '/playtester' || route.path.startsWith('/playtester/'));
const globalHotkeysEnabled = computed(() => !isActivePlaytesterRoute.value);
const globalNavigationHotkeys = computed(() => [
  {
    sequence: ['n', 'n'] as const,
    enabled: auth.authenticated && globalHotkeysEnabled.value,
    onTrigger: () => {
      void router.push(buildContextualNewDeckEditorLocation(route.path, route.query));
    },
  },
]);
const hoverModeOverrides = {
  gallery: hoverModePreferences.getOverrideHoverMode('gallery'),
  deckBuilder: hoverModePreferences.getOverrideHoverMode('deckBuilder'),
  deckDetail: hoverModePreferences.getOverrideHoverMode('deckDetail'),
} satisfies Record<HoverModeSurface, ReturnType<typeof hoverModePreferences.getOverrideHoverMode>>;
const activeHoverModeSurface = computed(() => resolveHoverModeSurfacePath(route.path));
const hoverModeHotkeyActions = computed(() => {
  if (!globalHotkeysEnabled.value) {
    return null;
  }
  const surface = activeHoverModeSurface.value;
  if (surface === null) {
    return null;
  }

  const hoverModeOverride = hoverModeOverrides[surface];
  return {
    setHoverMode: (mode: HoverMode) => {
      hoverModeOverride.value = mode;
    },
    clearHoverMode: () => {
      hoverModeOverride.value = null;
    },
  };
});

provideScrollContainer(scrollContainerRef);
usePrimarySearchHotkeys(globalHotkeysEnabled);
useGlobalNavigationHotkeys(globalNavigationHotkeys);
useHoverModeHotkeys(hoverModeHotkeyActions);

if (typeof window !== 'undefined') {
  useEventListener(
    window,
    'wheel',
    (event) => {
      if (!globalHotkeysEnabled.value) {
        return;
      }
      handleHoverPreviewScaleWheel(
        event,
        hoverModePreferences.hoverPreviewScale.value,
        (scale) => {
          hoverModePreferences.hoverPreviewScale.value = scale;
        },
      );
    },
    { passive: false },
  );
}

useResizeObserver(pageHeaderOutletRef, ([entry]) => {
  pageHeaderHeight.value = `${Math.round(entry.contentRect.height)}px`;
});

watch(
  () => route.fullPath,
  () => {
    mobileNavOpen.value = false;
  },
);

watch(isDesktop, (desktop) => {
  if (desktop) {
    mobileNavOpen.value = false;
  }
});
</script>
