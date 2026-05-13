<template>
  <section class="space-y-6">
    <div class="page-card">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-2">
          <h2 class="flex items-center gap-2 text-xl font-semibold text-slate-900">
            <Settings class="h-5 w-5 text-slate-500" />
            <span>Settings</span>
          </h2>
        </div>

        <div class="inline-flex w-full flex-wrap gap-2 rounded-xl border border-slate-200 bg-slate-50 p-1 lg:w-auto lg:flex-nowrap">
          <button
            class="inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition"
            type="button"
            :class="
              activeTab === 'catalog'
                ? 'bg-white text-sky-700 shadow-sm ring-1 ring-sky-100'
                : 'text-slate-600 hover:bg-white hover:text-slate-900'
            "
            @click="activeTab = 'catalog'"
          >
            <Tags class="h-4 w-4" />
            <span>Catalog</span>
          </button>
          <button
            class="inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition"
            type="button"
            :class="
              activeTab === 'templates'
                ? 'bg-white text-sky-700 shadow-sm ring-1 ring-sky-100'
                : 'text-slate-600 hover:bg-white hover:text-slate-900'
            "
            @click="activeTab = 'templates'"
          >
            <LayoutTemplate class="h-4 w-4" />
            <span>Templates</span>
          </button>
          <button
            v-if="auth.canAccessMaintenance"
            class="inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition"
            type="button"
            :class="
              activeTab === 'maintenance'
                ? 'bg-white text-sky-700 shadow-sm ring-1 ring-sky-100'
                : 'text-slate-600 hover:bg-white hover:text-slate-900'
            "
            @click="activeTab = 'maintenance'"
          >
            <Database class="h-4 w-4" />
            <span>Maintenance</span>
          </button>
        </div>
      </div>
    </div>

    <MaintenanceSettingsView v-if="activeTab === 'maintenance'" />
    <TemplatesSettingsView v-else-if="activeTab === 'templates'" />
    <CatalogSettingsView v-else />
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Database, LayoutTemplate, Settings, Tags } from 'lucide-vue-next';
import { useAuthStore } from '@/modules/auth/authStore';
import MaintenanceSettingsView from './views/MaintenanceSettingsView.vue';
import CatalogSettingsView from './views/CatalogSettingsView.vue';
import TemplatesSettingsView from './views/TemplatesSettingsView.vue';

const auth = useAuthStore();
const activeTab = ref<'maintenance' | 'catalog' | 'templates'>('catalog');
</script>
