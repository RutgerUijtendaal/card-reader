<template>
  <aside class="theme-card-frame-muted rounded-lg py-4 px-2">
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
            ? 'theme-selected-surface'
            : 'theme-ghost-button'
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
