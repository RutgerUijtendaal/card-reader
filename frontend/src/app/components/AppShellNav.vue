<template>
  <div
    class="app-sidebar app-scrollbar flex h-full flex-col overflow-y-auto"
    :class="collapsed ? 'px-3 py-4' : 'px-4 py-5'"
  >
    <div
      class="mb-4 flex w-full items-center gap-2"
      :class="collapsed ? 'justify-center' : 'justify-between'"
    >
      <button
        v-if="collapsed && !mobile"
        type="button"
        class="hover:theme-card-frame-muted group relative inline-flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl transition"
        aria-label="Expand sidebar"
        title="Expand sidebar"
        @click="$emit('toggleCollapse')"
      >
        <span class="absolute inset-0 rounded-xl" />
        <span
          class="absolute inset-0 flex items-center justify-center transition-opacity group-hover:opacity-0"
        >
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
        class="flex min-w-0 items-center gap-2.5 rounded-xl transition"
        :class="collapsed ? 'justify-center' : ''"
        to="/"
        @click="handleNavClick"
      >
        <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl">
          <img
            :src="cardLogoUrl"
            alt=""
            class="h-full w-full object-contain"
          >
        </span>
        <span
          v-if="!collapsed"
          class="app-sidebar-brand-name min-w-0 truncate"
        >Maity's Card Game</span>
      </RouterLink>

      <button
        v-if="mobile || (canCollapse && !collapsed)"
        type="button"
        class="app-sidebar-icon-button shrink-0"
        :aria-label="
          mobile ? 'Close navigation' : collapsed ? 'Expand sidebar' : 'Collapse sidebar'
        "
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

    <div class="mb-3 w-full">
      <CardPoolWorkspaceSwitcher
        :collapsed="collapsed"
        @selected="handleNavClick"
      />
    </div>

    <nav class="grid w-full gap-0.5">
      <AppShellNavLink
        :item="homeItem"
        :collapsed="collapsed"
        @navigate="handleNavClick"
      />

      <p
        v-if="!collapsed"
        class="app-sidebar-group-label"
        data-testid="workspace-nav-label"
      >
        {{ activePoolLabel }}
      </p>
      <div
        v-else
        class="app-sidebar-divider my-1.5"
        aria-hidden="true"
      />

      <AppShellNavLink
        v-for="item in poolItems"
        :key="item.label"
        :item="item"
        :collapsed="collapsed"
        :also-active="isAlsoActive(item)"
        @navigate="handleNavClick"
      />

      <template v-if="staffItems.length > 0">
        <p
          v-if="!collapsed"
          class="app-sidebar-group-label mt-2"
        >
          Workshop
        </p>
        <div
          v-else
          class="app-sidebar-divider my-1.5"
          aria-hidden="true"
        />

        <AppShellNavLink
          v-for="item in staffItems"
          :key="item.label"
          :item="item"
          :collapsed="collapsed"
          @navigate="handleNavClick"
        />
      </template>
    </nav>

    <div
      class="app-sidebar-divider mt-auto grid w-full gap-0.5 pt-3"
      data-testid="sidebar-account"
    >
      <AppShellNavLink
        v-for="item in accountItems"
        :key="item.label"
        :item="item"
        :collapsed="collapsed"
        @navigate="handleNavClick"
      />
      <AppHotkeysPanel :compact="collapsed" />
      <ThemeModeMenu :compact="collapsed" />

      <div
        v-if="auth.authenticated"
        class="app-sidebar-divider mt-2 pt-2"
      >
        <AppAccountMenu
          :compact="collapsed"
          @sign-out="signOut"
        />
      </div>

      <RouterLink
        v-else
        class="nav-link mt-2"
        :class="collapsed ? 'justify-center px-0' : ''"
        to="/login"
        :title="collapsed ? 'Sign in' : undefined"
        :aria-label="collapsed ? 'Sign in' : undefined"
        @click="handleNavClick"
      >
        <LogIn class="h-[1.125rem] w-[1.125rem] shrink-0" />
        <span v-if="!collapsed">Sign in</span>
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { ChevronRight, LogIn, PanelLeftClose, PanelLeftOpen, X } from 'lucide-vue-next';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import AppAccountMenu from '@/app/components/AppAccountMenu.vue';
import AppHotkeysPanel from '@/app/components/AppHotkeysPanel.vue';
import AppShellNavLink, { type AppShellNavItem } from '@/app/components/AppShellNavLink.vue';
import CardPoolWorkspaceSwitcher from '@/app/components/CardPoolWorkspaceSwitcher.vue';
import ThemeModeMenu from '@/app/components/ThemeModeMenu.vue';
import { useAccessRequestSummary } from '@/domain/access-requests/composables/useAccessRequestSummary';
import { useNotificationSummary } from '@/domain/notifications/composables/useNotificationSummary';
import { useReviewSummary } from '@/domain/review/composables/useReviewSummary';
import { useAuthStore } from '@/domain/session/store';
import {
  buildWorkspaceGalleryLocation,
  useCardPoolWorkspaceStore,
} from '@/domain/cards/cardPoolWorkspace';
import { CARD_POOL_ICONS } from '@/domain/cards/cardPoolIcons';
import { cardPoolLabel } from '@/domain/cards/cardPools';
import { APP_SECTION_ICONS } from '@/shared/components/app/appSectionIcons';

type NavItem = AppShellNavItem & {
  requiresAuth?: boolean;
  /** Other path prefixes that belong to this link, such as the Mine scope of a library. */
  alsoActiveFor?: string[];
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
const workspace = useCardPoolWorkspaceStore();
const router = useRouter();
const route = useRoute();
const cardLogoUrl = `${import.meta.env.BASE_URL}card_logo_transparent.webp`;
const { openReviewCount } = useReviewSummary();
const { unreadNotificationCount } = useNotificationSummary();
const { pendingAccessRequestCount } = useAccessRequestSummary();

const homeItem: NavItem = { label: 'Home', to: '/', icon: APP_SECTION_ICONS.home };
const activePoolLabel = computed(() => cardPoolLabel(workspace.activePool));

const canShowItem = (item: NavItem): boolean => !item.requiresAuth || auth.authenticated;

// Everything scoped to the selected workspace sits under its heading, so switching pools only
// changes this group.
const poolItems = computed<NavItem[]>(() => {
  const items: NavItem[] = [
    {
      label: 'Gallery',
      to: buildWorkspaceGalleryLocation(workspace.activePool),
      icon: CARD_POOL_ICONS[workspace.activePool],
      cardPool: workspace.activePool,
    },
  ];
  if (workspace.activePool === 'player') {
    items.push(
      { label: 'Decks', to: '/decks', icon: APP_SECTION_ICONS.decks, alsoActiveFor: ['/my/decks'] },
      {
        label: 'Build a deck',
        to: '/my/decks/new?return_to=my_decks',
        icon: APP_SECTION_ICONS.deckBuilder,
        requiresAuth: true,
      },
      { label: 'Playtester', to: '/playtester', icon: APP_SECTION_ICONS.playtester },
    );
  }
  if (workspace.activePool === 'evil') {
    items.push(
      {
        label: 'Encounters',
        to: '/encounters',
        icon: APP_SECTION_ICONS.encounters,
        alsoActiveFor: ['/my/encounters', '/staff/encounters'],
      },
      {
        label: 'Build Encounter',
        to: '/my/encounters/new',
        icon: APP_SECTION_ICONS.encounterBuilder,
        requiresAuth: true,
      },
    );
  }
  return items.filter(canShowItem);
});

const staffItems = computed<NavItem[]>(() => {
  if (!auth.canAccessStaffRoutes) {
    return [];
  }
  return [
    { label: 'Imports', to: '/imports', icon: APP_SECTION_ICONS.imports },
    { label: 'Operations', to: '/operations', icon: APP_SECTION_ICONS.operations },
    {
      label: 'Review Queue',
      to: '/review',
      icon: APP_SECTION_ICONS.review,
      badgeCount: openReviewCount.value,
    },
    {
      label: 'Admin',
      to: '/admin',
      icon: APP_SECTION_ICONS.admin,
      badgeCount: pendingAccessRequestCount.value,
    },
  ];
});

const accountItems = computed<NavItem[]>(() => {
  const items: NavItem[] = [
    {
      label: 'Notifications',
      to: '/notifications',
      icon: APP_SECTION_ICONS.notifications,
      requiresAuth: true,
      badgeCount: unreadNotificationCount.value,
    },
    { label: 'Settings', to: '/settings', icon: APP_SECTION_ICONS.settings },
  ];
  return items.filter(canShowItem);
});

// Builder routes such as /my/decks/new have their own link, so only the library path itself matches.
const isAlsoActive = (item: NavItem): boolean =>
  item.alsoActiveFor?.includes(route.path) ?? false;

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
  await router.push('/');
};
</script>
