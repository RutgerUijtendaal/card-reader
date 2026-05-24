<template>
  <div class="grid h-screen grid-cols-1 overflow-hidden lg:grid-cols-[260px_1fr]">
    <aside class="app-sidebar app-scrollbar flex h-full flex-col overflow-y-auto px-6 py-7">
      <h1 class="mb-4 text-2xl font-semibold">
        Cards
      </h1>
      <nav class="grid gap-2">
        <RouterLink
          class="nav-link"
          to="/cards"
        >
          <Images class="h-4 w-4" />
          <span>Gallery</span>
        </RouterLink>

        <RouterLink
          class="nav-link"
          to="/decks"
        >
          <BookOpen class="h-4 w-4" />
          <span>Decks</span>
        </RouterLink>

        <RouterLink
          class="nav-link"
          to="/settings"
        >
          <SlidersHorizontal class="h-4 w-4" />
          <span>Settings</span>
        </RouterLink>

        <RouterLink
          v-if="auth.canAccessStaffRoutes"
          class="nav-link"
          to="/import-jobs"
        >
          <Upload class="h-4 w-4" />
          <span>Import Jobs</span>
        </RouterLink>

        <RouterLink
          v-if="auth.canAccessStaffRoutes"
          class="nav-link"
          to="/review"
        >
          <ClipboardCheck class="h-4 w-4" />
          <span>Review Queue</span>
        </RouterLink>

        <RouterLink
          v-if="auth.canAccessStaffRoutes"
          class="nav-link"
          to="/admin"
        >
          <Settings class="h-4 w-4" />
          <span>Admin</span>
        </RouterLink>
      </nav>

      <div class="mt-auto space-y-4 pt-6">
        <div class="app-sidebar-divider pt-4">
          <ThemeModeMenu />
        </div>

        <div class="app-sidebar-divider pt-4">
          <RouterLink
            v-if="auth.authEnabled && !auth.authenticated"
            class="nav-link"
            to="/login"
          >
            <LogIn class="h-4 w-4" />
            <span>Sign in</span>
          </RouterLink>

          <button
            v-if="auth.authEnabled && auth.authenticated"
            class="nav-link w-full"
            type="button"
            @click="signOut"
          >
            <LogOut class="h-4 w-4" />
            <span>Sign out</span>
          </button>
        </div>
      </div>
    </aside>

    <main
      ref="scrollContainerRef"
      class="app-scrollbar h-full overflow-y-auto p-4 sm:p-6"
    >
      <RouterView />
    </main>
  </div>
  <Toaster
    rich-colors
    position="top-right"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { BookOpen, ClipboardCheck, Images, LogIn, LogOut, Settings, SlidersHorizontal, Upload } from 'lucide-vue-next';
import { Toaster } from 'vue-sonner';
import { useRouter } from 'vue-router';
import ThemeModeMenu from '@/components/app/ThemeModeMenu.vue';
import { provideScrollContainer } from '@/composables/useScrollContainer';
import { useAuthStore } from '@/modules/auth/authStore';

const auth = useAuthStore();
const router = useRouter();
const scrollContainerRef = ref<HTMLElement | null>(null);

provideScrollContainer(scrollContainerRef);

const signOut = async (): Promise<void> => {
  await auth.logout();
  await router.push('/cards');
};
</script>
