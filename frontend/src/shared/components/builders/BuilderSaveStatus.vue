<template>
  <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
    <div class="flex items-center gap-2">
      <component
        :is="busy ? LoaderCircle : dirty ? CloudUpload : Cloud"
        class="h-4 w-4 shrink-0"
        :class="{ 'animate-spin': busy }"
      />
      <span class="theme-section-title text-sm font-semibold">{{ label }}</span>
    </div>
    <label
      class="theme-section-muted flex items-center gap-2 text-sm font-semibold"
      :class="{ 'opacity-60': !canAutosync }"
    >
      <input
        v-model="autosync"
        class="h-4 w-4 rounded accent-emerald-400"
        type="checkbox"
        :disabled="!canAutosync"
      >
      <span>{{ saved ? 'Autosync' : 'Autosync after creation' }}</span>
    </label>
  </div>
</template>
<script setup lang="ts">
import { Cloud, CloudUpload, LoaderCircle } from 'lucide-vue-next';
defineProps<{
  busy: boolean;
  dirty: boolean;
  label: string;
  saved: boolean;
  canAutosync: boolean;
}>();
const autosync = defineModel<boolean>('autosync', { required: true });
</script>
