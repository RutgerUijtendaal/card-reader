<template>
  <section class="space-y-6">
    <AppPageHeader
      :icon="Settings"
      title="Admin"
      subtitle="Manage catalog data, versions, templates, card groups, users, and maintenance tools."
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
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
            :class="activeTab === 'versions' ? 'theme-tab-active' : ''"
            @click="setActiveTab('versions')"
          >
            <History class="h-4 w-4" />
            <span>Versions</span>
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
            class="theme-tab"
            type="button"
            :class="activeTab === 'card-merges' ? 'theme-tab-active' : ''"
            @click="setActiveTab('card-merges')"
          >
            <GitMerge class="h-4 w-4" />
            <span>Card merges</span>
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
      </template>
    </AppPageHeader>

    <MaintenanceAdminView v-if="activeTab === 'maintenance'" />
    <UsersAdminView v-else-if="activeTab === 'users'" />
    <CardMergesAdminView v-else-if="activeTab === 'card-merges'" />
    <CardGroupsAdminView v-else-if="activeTab === 'card-groups'" />
    <ContentVersionsAdminView v-else-if="activeTab === 'versions'" />
    <TemplatesAdminView v-else-if="activeTab === 'templates'" />
    <CatalogAdminView v-else />
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { Database, GitMerge, History, Layers3, LayoutTemplate, Settings, Tags, Users } from 'lucide-vue-next';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import {
  parseAdminTab,
  type AdminTab,
} from '@/modules/admin/adminRouteState';
import { useAdminRouteSync } from '@/modules/admin/composables/useAdminRouteSync';
import MaintenanceAdminView from './views/MaintenanceAdminView.vue';
import CatalogAdminView from './views/CatalogAdminView.vue';
import CardGroupsAdminView from './views/CardGroupsAdminView.vue';
import CardMergesAdminView from './views/CardMergesAdminView.vue';
import ContentVersionsAdminView from './views/ContentVersionsAdminView.vue';
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
