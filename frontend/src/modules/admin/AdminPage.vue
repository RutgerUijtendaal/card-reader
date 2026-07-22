<template>
  <section class="app-page-content space-y-6">
    <AppPageHeader
      :icon="Settings"
      title="Admin"
      subtitle="Manage catalog data, versions, templates, card groups, users, and maintenance tools."
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <div class="theme-tablist">
          <AppHeaderAction
            :icon="Tags"
            label="Catalog"
            short-label="Catalog"
            variant="tab"
            :active="activeTab === 'catalog'"
            @click="setActiveTab('catalog')"
          />
          <AppHeaderAction
            :icon="LayoutTemplate"
            label="Templates"
            short-label="Templates"
            variant="tab"
            :active="activeTab === 'templates'"
            @click="setActiveTab('templates')"
          />
          <AppHeaderAction
            :icon="History"
            label="Versions"
            short-label="Versions"
            variant="tab"
            :active="activeTab === 'versions'"
            @click="setActiveTab('versions')"
          />
          <AppHeaderAction
            :icon="Images"
            label="Card backs"
            short-label="Backs"
            variant="tab"
            :active="activeTab === 'card-backs'"
            @click="setActiveTab('card-backs')"
          />
          <AppHeaderAction
            :icon="Layers3"
            label="Card groups"
            short-label="Groups"
            variant="tab"
            :active="activeTab === 'card-groups'"
            @click="setActiveTab('card-groups')"
          />
          <AppHeaderAction
            :icon="GitMerge"
            label="Card merges"
            short-label="Merges"
            variant="tab"
            :active="activeTab === 'card-merges'"
            @click="setActiveTab('card-merges')"
          />
          <AppHeaderAction
            v-if="auth.canManageUsers"
            :icon="Users"
            label="Users"
            short-label="Users"
            variant="tab"
            :active="activeTab === 'users'"
            @click="setActiveTab('users')"
          >
            <template #trailing>
              <span
                v-if="pendingAccessRequestCount > 0"
                class="theme-pill theme-pill-success ml-1 px-2 py-0.5 text-[11px] font-semibold"
              >
                {{ pendingAccessRequestCount }}
              </span>
            </template>
          </AppHeaderAction>
          <AppHeaderAction
            v-if="auth.canAccessMaintenance"
            :icon="Database"
            label="Maintenance"
            short-label="System"
            variant="tab"
            :active="activeTab === 'maintenance'"
            @click="setActiveTab('maintenance')"
          />
        </div>
      </template>
    </AppPageHeader>

    <MaintenanceAdminView v-if="activeTab === 'maintenance'" />
    <UsersAdminView v-else-if="activeTab === 'users'" />
    <CardMergesAdminView v-else-if="activeTab === 'card-merges'" />
    <CardGroupsAdminView v-else-if="activeTab === 'card-groups'" />
    <CardBacksAdminView v-else-if="activeTab === 'card-backs'" />
    <ContentVersionsAdminView v-else-if="activeTab === 'versions'" />
    <TemplatesAdminView v-else-if="activeTab === 'templates'" />
    <CatalogAdminView v-else />
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { Database, GitMerge, History, Images, Layers3, LayoutTemplate, Settings, Tags, Users } from 'lucide-vue-next';
import AppHeaderAction from '@/components/app/AppHeaderAction.vue';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import { useAccessRequestSummary } from '@/composables/useAccessRequestSummary';
import { useAuthStore } from '@/modules/auth/authStore';
import {
  parseAdminTab,
  type AdminTab,
} from '@/composables/admin/adminRouteState';
import { useAdminRouteSync } from '@/modules/admin/composables/useAdminRouteSync';
import MaintenanceAdminView from './views/MaintenanceAdminView.vue';
import CatalogAdminView from './views/CatalogAdminView.vue';
import CardGroupsAdminView from './views/CardGroupsAdminView.vue';
import CardBacksAdminView from './views/CardBacksAdminView.vue';
import CardMergesAdminView from './views/CardMergesAdminView.vue';
import ContentVersionsAdminView from './views/ContentVersionsAdminView.vue';
import TemplatesAdminView from './views/TemplatesAdminView.vue';
import UsersAdminView from './views/UsersAdminView.vue';

const auth = useAuthStore();
const { pendingAccessRequestCount } = useAccessRequestSummary();
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
