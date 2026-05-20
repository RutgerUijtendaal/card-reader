<template>
  <section class="space-y-6">
    <div class="page-card">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-2">
          <h2 class="theme-section-title flex items-center gap-2 text-xl font-semibold">
            <Settings class="theme-section-muted h-5 w-5" />
            <span>Settings</span>
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

    <MaintenanceSettingsView v-if="activeTab === 'maintenance'" />
    <CardGroupsSettingsView v-else-if="activeTab === 'card-groups'" />
    <TemplatesSettingsView v-else-if="activeTab === 'templates'" />
    <CatalogSettingsView v-else />
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { Database, Layers3, LayoutTemplate, Settings, Tags } from 'lucide-vue-next';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/modules/auth/authStore';
import {
  buildSettingsQuery,
  parseSettingsTab,
  type SettingsTab,
} from '@/modules/settings/settingsRouteState';
import MaintenanceSettingsView from './views/MaintenanceSettingsView.vue';
import CatalogSettingsView from './views/CatalogSettingsView.vue';
import CardGroupsSettingsView from './views/CardGroupsSettingsView.vue';
import TemplatesSettingsView from './views/TemplatesSettingsView.vue';

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const activeTab = ref<SettingsTab>('catalog');

const setActiveTab = (tab: SettingsTab, options: { syncRoute?: boolean } = {}): void => {
  activeTab.value = tab;
  if (options.syncRoute === false) {
    return;
  }
  void router.replace({
    path: '/settings',
    query: buildSettingsQuery(route.query, { tab }),
  });
};

watch(
  () => route.query,
  (query) => {
    const nextTab = parseSettingsTab(query, { allowMaintenance: auth.canAccessMaintenance });
    if (activeTab.value !== nextTab) {
      setActiveTab(nextTab, { syncRoute: false });
    }
  },
  { immediate: true },
);
</script>
