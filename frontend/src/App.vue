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

    <div class="min-w-0 flex-1 overflow-hidden">
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

      <main
        ref="scrollContainerRef"
        class="app-scrollbar h-full overflow-y-auto p-4 pt-1 sm:p-6 sm:pt-2 lg:p-6"
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
import { useLocalStorage, useMediaQuery } from '@vueuse/core';
import { Menu } from 'lucide-vue-next';
import { Toaster } from 'vue-sonner';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import AppShellNav from '@/components/app/AppShellNav.vue';
import { useGlobalNavigationHotkeys, usePrimarySearchHotkeys } from '@/composables/useHotkeys';
import { provideScrollContainer } from '@/composables/useScrollContainer';
import { useAuthStore } from '@/modules/auth/authStore';
import { buildContextualNewDeckEditorLocation } from '@/composables/decks/deckRouteState';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const scrollContainerRef = ref<HTMLElement | null>(null);
const isDesktop = useMediaQuery('(min-width: 1024px)');
const mobileNavOpen = ref(false);
const isSidebarCollapsed = useLocalStorage('card-reader.sidebar-collapsed', false, {
  writeDefaults: true,
});
const cardLogoUrl = `${import.meta.env.BASE_URL}card_logo_transparent.webp`;
const globalNavigationHotkeys = computed(() => [
  {
    sequence: ['n', 'n'] as const,
    enabled: auth.authenticated,
    onTrigger: () => {
      void router.push(buildContextualNewDeckEditorLocation(route.path, route.query));
    },
  },
]);

provideScrollContainer(scrollContainerRef);
usePrimarySearchHotkeys();
useGlobalNavigationHotkeys(globalNavigationHotkeys);

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
