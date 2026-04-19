<template>
  <section class="space-y-6">
    <div class="page-card space-y-2">
      <h2 class="flex items-center gap-2 text-xl font-semibold text-slate-900">
        <Settings class="h-5 w-5 text-slate-500" />
        <span>Settings</span>
      </h2>
      <p class="text-sm text-slate-600">Maintenance and catalog management.</p>
    </div>

    <div class="page-card">
      <div class="flex flex-wrap gap-2">
        <button
          class="btn-secondary inline-flex items-center gap-2"
          type="button"
          :class="activeTab === 'catalog' ? 'border-sky-300 bg-sky-50 text-sky-700' : ''"
          @click="activeTab = 'catalog'"
        >
          <Tags class="h-4 w-4" />
          <span>Catalog</span>
        </button>
        <button
          class="btn-secondary inline-flex items-center gap-2"
          type="button"
          :class="activeTab === 'maintenance' ? 'border-sky-300 bg-sky-50 text-sky-700' : ''"
          @click="activeTab = 'maintenance'"
        >
          <Database class="h-4 w-4" />
          <span>Maintenance</span>
        </button>
      </div>
    </div>
    <MaintenanceSettingsView v-if="activeTab === 'maintenance'" />
    <CatalogSettingsView v-else />
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Database, Settings, Tags } from 'lucide-vue-next';
import MaintenanceSettingsView from './views/MaintenanceSettingsView.vue';
import CatalogSettingsView from './views/CatalogSettingsView.vue';

const activeTab = ref<'maintenance' | 'catalog'>('catalog');
</script>
