<template>
  <section class="space-y-6">
    <div class="page-card">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-2">
          <h2 class="theme-section-title flex items-center gap-2 text-xl font-semibold">
            <Settings class="theme-section-muted h-5 w-5" />
            <span>Admin</span>
          </h2>
        </div>

        <div class="theme-tablist">
          <button
            class="theme-tab"
            type="button"
            :class="activeTab === 'catalog' ? 'theme-tab-active' : ''"
            @click="setActiveTab('catalog')"
          >
            <Tags class="h-4 w-4" />
            <span>Catalog</span>
          </button>
          <button
            class="theme-tab"
            type="button"
            :class="activeTab === 'templates' ? 'theme-tab-active' : ''"
            @click="setActiveTab('templates')"
          >
            <LayoutTemplate class="h-4 w-4" />
            <span>Templates</span>
          </button>
          <button
            class="theme-tab"
            type="button"
            :class="activeTab === 'card-groups' ? 'theme-tab-active' : ''"
            @click="setActiveTab('card-groups')"
          >
            <Layers3 class="h-4 w-4" />
            <span>Card groups</span>
          </button>
          <button
            v-if="auth.canManageUsers"
            class="theme-tab"
            type="button"
            :class="activeTab === 'users' ? 'theme-tab-active' : ''"
            @click="setActiveTab('users')"
          >
            <Users class="h-4 w-4" />
            <span>Users</span>
          </button>
          <button
            v-if="auth.canAccessMaintenance"
            class="theme-tab"
            type="button"
            :class="activeTab === 'maintenance' ? 'theme-tab-active' : ''"
            @click="setActiveTab('maintenance')"
          >
            <Database class="h-4 w-4" />
            <span>Maintenance</span>
          </button>
        </div>
      </div>
    </div>

    <MaintenanceAdminView v-if="activeTab === 'maintenance'" />
    <UsersAdminView v-else-if="activeTab === 'users'" />
    <CardGroupsAdminView v-else-if="activeTab === 'card-groups'" />
    <TemplatesAdminView v-else-if="activeTab === 'templates'" />
    <CatalogAdminView v-else />
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { Database, Layers3, LayoutTemplate, Settings, Tags, Users } from 'lucide-vue-next';
import { useAuthStore } from '@/modules/auth/authStore';
import {
  parseAdminTab,
  type AdminTab,
} from '@/modules/admin/adminRouteState';
import { useAdminRouteSync } from '@/modules/admin/composables/useAdminRouteSync';
import MaintenanceAdminView from './views/MaintenanceAdminView.vue';
import CatalogAdminView from './views/CatalogAdminView.vue';
import CardGroupsAdminView from './views/CardGroupsAdminView.vue';
import TemplatesAdminView from './views/TemplatesAdminView.vue';
import UsersAdminView from './views/UsersAdminView.vue';

const auth = useAuthStore();
const { route, replaceAdminQuery } = useAdminRouteSync();
const activeTab = ref<AdminTab>('catalog');

const setActiveTab = (tab: AdminTab, options: { syncRoute?: boolean } = {}): void => {
  activeTab.value = tab;
  if (options.syncRoute === false) {
    return;
  }
  replaceAdminQuery({ tab });
};

watch(
  () => route.query,
  (query) => {
    const nextTab = parseAdminTab(query, {
      allowUsers: auth.canManageUsers,
      allowMaintenance: auth.canAccessMaintenance,
    });
    if (activeTab.value !== nextTab) {
      setActiveTab(nextTab, { syncRoute: false });
    }
  },
  { immediate: true },
);
</script>
