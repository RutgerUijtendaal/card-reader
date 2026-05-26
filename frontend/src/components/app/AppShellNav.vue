<template>
  <div
    class="app-sidebar app-scrollbar flex h-full flex-col overflow-y-auto"
    :class="collapsed ? 'px-3 py-4' : 'px-5 py-6'"
  >
    <div
      class="mb-5 flex w-full items-center gap-3"
      :class="collapsed ? 'justify-center' : 'justify-between'"
    >
      <button
        v-if="collapsed && !mobile"
        type="button"
        class="hover:theme-card-frame-muted group relative inline-flex h-11 w-11 items-center justify-center overflow-hidden rounded-xl transition"
        aria-label="Expand sidebar"
        title="Expand sidebar"
        @click="$emit('toggleCollapse')"
      >
        <span class="absolute inset-0 rounded-xl" />
        <span class="absolute inset-0 flex items-center justify-center transition-opacity group-hover:opacity-0">
          <img
            :src="cardLogoUrl"
            alt=""
            class="h-full w-full object-contain"
          >
        </span>
        <ChevronRight
          class="pointer-events-none absolute inset-0 m-auto h-4 w-4 text-white opacity-0 transition-opacity group-hover:opacity-100"
        />
      </button>

      <RouterLink
        v-else
        class="flex min-w-0 items-center gap-3 rounded-xl transition"
        :class="collapsed ? 'justify-center' : ''"
        to="/cards"
        @click="handleNavClick"
      >
        <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl">
          <img
            :src="cardLogoUrl"
            alt=""
            class="h-full w-full object-contain"
          >
        </span>
        <span
          v-if="!collapsed"
          class="min-w-0"
        >
          <span class="block truncate text-base font-semibold text-white">Maity's Card Game</span>
        </span>
      </RouterLink>

      <button
        v-if="mobile || (canCollapse && !collapsed)"
        type="button"
        class="nav-link shrink-0"
        :class="collapsed ? 'justify-center px-0' : ''"
        :aria-label="mobile ? 'Close navigation' : collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        :title="mobile ? 'Close navigation' : collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="mobile ? $emit('closeMobile') : $emit('toggleCollapse')"
      >
        <X
          v-if="mobile"
          class="h-[1.125rem] w-[1.125rem]"
        />
        <PanelLeftOpen
          v-else-if="collapsed"
          class="h-[1.125rem] w-[1.125rem]"
        />
        <PanelLeftClose
          v-else
          class="h-[1.125rem] w-[1.125rem]"
        />
      </button>
    </div>

    <nav class="grid w-full gap-2">
      <RouterLink
        v-for="item in visibleItems"
        :key="item.to"
        class="nav-link"
        :class="collapsed ? 'justify-center px-0' : ''"
        :to="item.to"
        :title="collapsed ? item.label : undefined"
        :aria-label="collapsed ? item.label : undefined"
        @click="handleNavClick"
      >
        <component
          :is="item.icon"
          class="h-[1.125rem] w-[1.125rem] shrink-0"
        />
        <span v-if="!collapsed">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="mt-auto w-full space-y-4 pt-6">
      <div class="app-sidebar-divider pt-4">
        <div :class="collapsed ? 'flex justify-center' : ''">
          <ThemeModeMenu :compact="collapsed" />
        </div>
      </div>

      <div class="app-sidebar-divider pt-4">
        <RouterLink
          v-if="auth.authEnabled && !auth.authenticated"
          class="nav-link"
          :class="collapsed ? 'w-full justify-center px-0' : 'w-full'"
          to="/login"
          :title="collapsed ? 'Sign in' : undefined"
          :aria-label="collapsed ? 'Sign in' : undefined"
          @click="handleNavClick"
        >
          <LogIn class="h-[1.125rem] w-[1.125rem] shrink-0" />
          <span v-if="!collapsed">Sign in</span>
        </RouterLink>

        <button
          v-if="auth.authEnabled && auth.authenticated"
          class="nav-link"
          :class="collapsed ? 'w-full justify-center px-0' : 'w-full'"
          type="button"
          :title="collapsed ? 'Sign out' : undefined"
          :aria-label="collapsed ? 'Sign out' : undefined"
          @click="signOut"
        >
          <LogOut class="h-[1.125rem] w-[1.125rem] shrink-0" />
          <span v-if="!collapsed">Sign out</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { BookOpen, ChevronRight, ClipboardCheck, Folders, Images, LogIn, LogOut, PanelLeftClose, PanelLeftOpen, Settings, SlidersHorizontal, Upload, X } from 'lucide-vue-next';
import { RouterLink, useRouter } from 'vue-router';
import ThemeModeMenu from '@/components/app/ThemeModeMenu.vue';
import { useAuthStore } from '@/modules/auth/authStore';

type NavItem = {
  label: string;
  to: string;
  icon: typeof Images;
  requiresStaff?: boolean;
  requiresAuth?: boolean;
};

const props = withDefaults(
  defineProps<{
    collapsed?: boolean;
    mobile?: boolean;
    canCollapse?: boolean;
  }>(),
  {
    collapsed: false,
    mobile: false,
    canCollapse: false,
  },
);

const emit = defineEmits<{
  toggleCollapse: [];
  closeMobile: [];
}>();

const auth = useAuthStore();
const router = useRouter();
const cardLogoUrl = `${import.meta.env.BASE_URL}card_logo_transparent.webp`;

const items: NavItem[] = [
  { label: 'Gallery', to: '/cards', icon: Images },
  { label: 'Decks', to: '/decks', icon: BookOpen },
  { label: 'My Decks', to: '/my/decks', icon: Folders, requiresAuth: true },
  { label: 'Settings', to: '/settings', icon: SlidersHorizontal },
  { label: 'Import Jobs', to: '/import-jobs', icon: Upload, requiresStaff: true },
  { label: 'Review Queue', to: '/review', icon: ClipboardCheck, requiresStaff: true },
  { label: 'Admin', to: '/admin', icon: Settings, requiresStaff: true },
];

const visibleItems = computed(() =>
  items.filter((item) => {
    if (item.requiresStaff && !auth.canAccessStaffRoutes) {
      return false;
    }
    if (item.requiresAuth && auth.authEnabled && !auth.authenticated) {
      return false;
    }
    return true;
  }),
);

const handleNavClick = (): void => {
  if (props.mobile) {
    emit('closeMobile');
  }
};

const signOut = async (): Promise<void> => {
  await auth.logout();
  if (props.mobile) {
    emit('closeMobile');
  }
  await router.push('/cards');
};
</script>
