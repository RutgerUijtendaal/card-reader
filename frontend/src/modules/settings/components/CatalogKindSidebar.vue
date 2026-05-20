<template>
  <aside class="rounded-lg border border-slate-200 p-2 dark:border-slate-700 dark:bg-slate-950/40">
    <div
      v-for="group in catalogKindGroups"
      :key="group.label"
      class="mb-3 last:mb-0"
    >
      <div class="theme-kicker px-3 pb-2 text-[11px] font-semibold uppercase tracking-[0.18em]">
        {{ group.label }}
      </div>
      <button
        v-for="kind in group.kinds"
        :key="kind"
        class="mb-1 w-full rounded-md px-3 py-2 text-left text-sm font-medium transition last:mb-0"
        :class="
          selectedKind === kind
            ? 'bg-sky-100 text-sky-800 dark:bg-sky-950/70 dark:text-sky-100'
            : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
        "
        type="button"
        @click="emit('select', kind)"
      >
        {{ kindLabel(kind) }}
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { CatalogKind } from '@/modules/settings/types';

defineProps<{
  catalogKindGroups: { label: string; kinds: CatalogKind[] }[];
  selectedKind: CatalogKind;
  kindLabel: (kind: CatalogKind) => string;
}>();

const emit = defineEmits<{
  (e: 'select', kind: CatalogKind): void;
}>();
</script>
