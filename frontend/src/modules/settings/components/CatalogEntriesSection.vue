<template>
  <section class="flex min-h-0 flex-col rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-slate-700 dark:bg-slate-950/55">
    <div class="flex flex-col gap-3 border-b border-slate-200 pb-4 dark:border-slate-700">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h4 class="theme-section-title text-sm font-semibold">
            {{ kindLabel(selectedKind) }}
          </h4>
          <p class="theme-section-muted mt-1 text-xs">
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
        <span class="theme-kicker mb-1 block text-xs font-medium uppercase tracking-[0.16em]">
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
      class="theme-section-muted py-8 text-sm"
    >
      {{ emptyState }}
    </div>

    <div
      v-else-if="currentRows.length === 0"
      class="theme-section-muted py-8 text-sm"
    >
      No matching entries.
    </div>

    <div
      v-else
      class="app-scrollbar mt-4 min-h-0 space-y-2 overflow-y-auto pr-1"
    >
      <button
        v-for="entry in currentRows"
        :key="entry.id"
        class="w-full rounded-xl border px-3 py-3 text-left transition"
        :class="
          selectedEntryId === entry.id
            ? 'border-sky-300 bg-sky-50 shadow-sm dark:border-sky-700/80 dark:bg-sky-950/55'
            : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-500 dark:hover:bg-slate-800'
        "
        type="button"
        @click="emit('select-entry', entry.id)"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="theme-section-title truncate text-sm font-semibold">
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

        <div
          v-if="'symbol_type' in entry"
          class="mt-3 flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300"
        >
          <span
            class="h-2.5 w-2.5 rounded-full"
            :class="entry.enabled ? 'bg-emerald-500' : 'bg-rose-500'"
          />
          <span>{{ entry.text_token ? `Token ${entry.text_token}` : 'No text token' }}</span>
        </div>
        <p
          v-else
          class="mt-3 text-xs text-slate-600 dark:text-slate-300"
        >
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
        label: String(entry.occurrence_count),
        tone: 'bg-sky-100 text-sky-700 dark:bg-sky-900/80 dark:text-sky-100 dark:ring-1 dark:ring-sky-700/70',
      },
      {
        label: entry.status,
        tone:
          entry.status === 'accepted'
            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/80 dark:text-emerald-100 dark:ring-1 dark:ring-emerald-700/70'
            : entry.status === 'rejected'
              ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/80 dark:text-amber-100 dark:ring-1 dark:ring-amber-700/70'
              : 'bg-sky-100 text-sky-700 dark:bg-sky-900/80 dark:text-sky-100 dark:ring-1 dark:ring-sky-700/70',
      },
    ];
  }

  if ('symbol_type' in entry) {
    return [
      {
        label: String(entry.linked_card_count ?? 0),
        tone: 'bg-sky-100 text-sky-700 dark:bg-sky-900/80 dark:text-sky-100 dark:ring-1 dark:ring-sky-700/70',
      },
      {
        label: entry.symbol_type || 'symbol',
        tone: 'bg-slate-100 text-slate-600 dark:bg-slate-800/95 dark:text-slate-100 dark:ring-1 dark:ring-slate-600/80',
      },
    ];
  }

  return [
    {
      label: String(entry.linked_card_count ?? 0),
      tone: 'bg-sky-100 text-sky-700 dark:bg-sky-900/80 dark:text-sky-100 dark:ring-1 dark:ring-sky-700/70',
    },
    {
      label: `${entry.identifiers.length} identifiers`,
      tone: 'bg-slate-100 text-slate-600 dark:bg-slate-800/95 dark:text-slate-100 dark:ring-1 dark:ring-slate-600/80',
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
    return entry.text_token ? `Token ${entry.text_token}` : 'No text token';
  }

  if (entry.identifiers.length === 0) {
    return 'No identifiers configured.';
  }

  return entry.identifiers.slice(0, 3).join(', ');
};
</script>
