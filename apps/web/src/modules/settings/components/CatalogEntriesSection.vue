<template>
  <section class="flex min-h-0 flex-col rounded-xl border border-slate-200 bg-white/80 p-4">
    <div class="flex flex-col gap-3 border-b border-slate-200 pb-4">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h4 class="text-sm font-semibold text-slate-900">
            {{ kindLabel(selectedKind) }}
          </h4>
          <p class="mt-1 text-xs text-slate-500">
            {{ currentRows.length }} of {{ totalCount }} shown
          </p>
        </div>
        <button
          v-if="canCreate"
          class="btn-secondary px-3 py-2"
          type="button"
          @click="emit('create-new')"
        >
          New {{ kindItemLabel(selectedKind) }}
        </button>
      </div>

      <label class="block">
        <span class="mb-1 block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
          Filter entries
        </span>
        <input
          :value="searchTerm"
          class="input-base"
          :placeholder="searchPlaceholder"
          @input="emit('update:search-term', ($event.target as HTMLInputElement).value)"
        >
      </label>
    </div>

    <div
      v-if="totalCount === 0"
      class="py-8 text-sm text-slate-500"
    >
      {{ emptyState }}
    </div>

    <div
      v-else-if="currentRows.length === 0"
      class="py-8 text-sm text-slate-500"
    >
      No matching entries.
    </div>

    <div
      v-else
      class="mt-4 min-h-0 space-y-2 overflow-y-auto pr-1"
    >
      <button
        v-for="entry in currentRows"
        :key="entry.id"
        class="w-full rounded-xl border px-3 py-3 text-left transition"
        :class="
          selectedEntryId === entry.id
            ? 'border-sky-300 bg-sky-50 shadow-sm'
            : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
        "
        type="button"
        @click="emit('select-entry', entry.id)"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="truncate text-sm font-semibold text-slate-900">
              {{ entry.label || entry.key || 'Untitled entry' }}
            </div>
          </div>
          <div class="flex items-center justify-end gap-2">
            <span
              v-for="badge in entryBadges(entry)"
              :key="badge.label"
              class="rounded-full px-2 py-1 text-[11px] font-medium text-nowrap"
              :class="badge.tone"
            >
              {{ badge.label }}
            </span>
          </div>
        </div>

        <p class="mt-3 text-xs text-slate-600">
          {{ entryPreview(entry) }}
        </p>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { CatalogKind, CatalogRow } from '@/modules/settings/types';
import { isSuggestionRecord } from '@/modules/settings/composables/catalogSettingsUtils';

const props = defineProps<{
  selectedKind: CatalogKind;
  searchTerm: string;
  totalCount: number;
  currentRows: CatalogRow[];
  selectedEntryId: string | null;
  kindLabel: (kind: CatalogKind) => string;
  kindItemLabel: (kind: CatalogKind) => string;
  canCreate: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:search-term', value: string): void;
  (e: 'create-new'): void;
  (e: 'select-entry', entryId: string): void;
}>();

const searchPlaceholder = computed(() =>
  props.canCreate
    ? `Search ${props.kindLabel(props.selectedKind).toLowerCase()} by label, key, or metadata`
    : `Search ${props.kindLabel(props.selectedKind).toLowerCase()} suggestions`,
);

const emptyState = computed(() =>
  props.canCreate
    ? `No entries yet. Create the first ${props.kindItemLabel(props.selectedKind).toLowerCase()} from here.`
    : `No suggestions yet.`,
);

const entryBadges = (entry: CatalogRow): { label: string; tone: string }[] => {
  if (isSuggestionRecord(entry)) {
    return [
      {
        label: `${entry.occurrence_count} matches`,
        tone: 'bg-slate-100 text-slate-600',
      },
      {
        label: entry.status,
        tone:
          entry.status === 'accepted'
            ? 'bg-emerald-100 text-emerald-700'
            : entry.status === 'rejected'
              ? 'bg-amber-100 text-amber-700'
              : 'bg-sky-100 text-sky-700',
      },
    ];
  }

  if ('symbol_type' in entry) {
    return [
      {
        label: entry.enabled ? 'Enabled' : 'Disabled',
        tone: entry.enabled
          ? 'bg-emerald-100 text-emerald-700'
          : 'bg-amber-100 text-amber-700',
      },
      {
        label: entry.symbol_type || 'symbol',
        tone: 'bg-slate-100 text-slate-600',
      },
    ];
  }

  return [
    {
      label: `${entry.identifiers.length} identifiers`,
      tone: 'bg-slate-100 text-slate-600',
    },
  ];
};

const entryPreview = (entry: CatalogRow): string => {
  if (isSuggestionRecord(entry)) {
    if (entry.accepted_target) {
      return `Accepted as ${entry.accepted_target.label}`;
    }
    if (entry.occurrences.length === 0) {
      return 'No linked cards yet.';
    }
    return entry.occurrences
      .slice(0, 2)
      .map((occurrence) => `${occurrence.card_label}: ${occurrence.source_text}`)
      .join(' • ');
  }

  if ('symbol_type' in entry) {
    return [entry.text_token ? `Token ${entry.text_token}` : 'No text token'].join(' • ');
  }

  if (entry.identifiers.length === 0) {
    return 'No identifiers configured.';
  }

  return entry.identifiers.slice(0, 3).join(', ');
};
</script>
