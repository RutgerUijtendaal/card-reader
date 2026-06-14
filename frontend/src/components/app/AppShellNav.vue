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
          <span class="block truncate text-sm font-semibold text-white">Maity's Card Game</span>
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
      <template
        v-for="item in publicItems"
        :key="item.to"
      >
        <RouterLink
          class="nav-link relative"
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
          <span
            v-if="collapsed && item.badgeCount && item.badgeCount > 0"
            class="nav-indicator-dot"
            aria-hidden="true"
          />
          <span
            v-if="!collapsed && item.badgeCount && item.badgeCount > 0"
            class="nav-badge theme-pill theme-pill-success ml-auto text-[11px] font-semibold"
          >
            {{ item.badgeCount }}
          </span>
        </RouterLink>
      </template>

      <div
        v-if="staffItems.length > 0"
        class="app-sidebar-divider my-2"
      />

      <template
        v-for="item in staffItems"
        :key="item.to"
      >
        <RouterLink
          class="nav-link relative"
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
          <span
            v-if="collapsed && item.badgeCount && item.badgeCount > 0"
            class="nav-indicator-dot"
            aria-hidden="true"
          />
          <span
            v-if="!collapsed && item.badgeCount && item.badgeCount > 0"
            class="nav-badge theme-pill theme-pill-success ml-auto text-[11px] font-semibold"
          >
            {{ item.badgeCount }}
          </span>
        </RouterLink>
      </template>
    </nav>

    <div class="mt-auto w-full space-y-4 pt-6">
      <div class="app-sidebar-divider pt-4">
        <div :class="collapsed ? 'flex justify-center' : ''">
          <AppHotkeysPanel :compact="collapsed" />
        </div>
      </div>

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
import { Bell, BookOpen, ChevronRight, ClipboardCheck, Folders, Gamepad2, Hammer, Images, LogIn, LogOut, PanelLeftClose, PanelLeftOpen, Settings, SlidersHorizontal, Upload, X } from 'lucide-vue-next';
import { RouterLink, useRouter } from 'vue-router';
import AppHotkeysPanel from '@/components/app/AppHotkeysPanel.vue';
import ThemeModeMenu from '@/components/app/ThemeModeMenu.vue';
import { useNotificationSummary } from '@/composables/useNotificationSummary';
import { useReviewSummary } from '@/composables/useReviewSummary';
import { useAuthStore } from '@/modules/auth/authStore';

type NavItem = {
  label: string;
  to: string;
  icon: typeof Images;
  requiresStaff?: boolean;
  requiresAuth?: boolean;
  requiresAuthenticatedUser?: boolean;
  badgeCount?: number;
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
const { openParseFlagItemCount } = useReviewSummary();
const { unreadNotificationCount } = useNotificationSummary();

const items = computed<NavItem[]>(() => [
  { label: 'Gallery', to: '/cards', icon: Images },
  { label: 'Decks', to: '/decks', icon: BookOpen },
  { label: 'Playtester', to: '/playtester', icon: Gamepad2 },
  { label: 'My Decks', to: '/my/decks', icon: Folders, requiresAuth: true },
  { label: 'Build a deck', to: '/my/decks/new?return_to=my_decks', icon: Hammer, requiresAuth: true },
  { label: 'Notifications', to: '/notifications', icon: Bell, requiresAuthenticatedUser: true, badgeCount: unreadNotificationCount.value },
  { label: 'Settings', to: '/settings', icon: SlidersHorizontal },
  { label: 'Import Jobs', to: '/import-jobs', icon: Upload, requiresStaff: true },
  { label: 'Review Queue', to: '/review', icon: ClipboardCheck, requiresStaff: true, badgeCount: openParseFlagItemCount.value },
  { label: 'Admin', to: '/admin', icon: Settings, requiresStaff: true },
]);

const canShowItem = (item: NavItem): boolean => {
  if (item.requiresStaff && !auth.canAccessStaffRoutes) {
    return false;
  }
  if (item.requiresAuth && auth.authEnabled && !auth.authenticated) {
    return false;
  }
  if (item.requiresAuthenticatedUser && (!auth.authEnabled || !auth.authenticated)) {
    return false;
  }
  return true;
};

const publicItems = computed(() => items.value.filter((item) => !item.requiresStaff && canShowItem(item)));
const staffItems = computed(() => items.value.filter((item) => item.requiresStaff && canShowItem(item)));

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
