<template>
  <section class="theme-panel-shell flex min-h-0 flex-col p-4">
    <div class="theme-divider flex flex-col gap-3 border-b pb-4">
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
            ? 'theme-selected-surface-strong'
            : 'theme-card-frame hover:-translate-y-0.5'
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
              class="theme-pill text-nowrap"
              :class="badge.tone"
            >
              {{ badge.label }}
            </span>
          </div>
        </div>

        <div
          v-if="'symbol_type' in entry"
          class="theme-inline-muted mt-3 flex items-center gap-2 text-xs"
        >
          <span
            class="h-2.5 w-2.5 rounded-full"
            :class="entry.enabled ? 'bg-emerald-500' : 'bg-rose-500'"
          />
          <span>{{ entry.text_token ? `Token ${entry.text_token}` : 'No text token' }}</span>
        </div>
        <p
          v-else
          class="theme-inline-muted mt-3 text-xs"
        >
          {{ entryPreview(entry) }}
        </p>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { CatalogKind, CatalogRow } from '@/modules/admin/types';
import { isSuggestionRecord } from '@/modules/admin/composables/catalogAdminUtils';

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

const metadataToneForKind = (kind: CatalogKind): string => {
  switch (kind) {
    case 'keywords':
      return 'theme-pill-keyword';
    case 'tags':
    case 'suggested-tags':
      return 'theme-pill-success';
    case 'types':
    case 'suggested-types':
      return 'theme-pill-warning';
    case 'symbols':
      return 'theme-pill-symbol';
    default:
      return 'theme-pill-neutral';
  }
};

const entryBadges = (entry: CatalogRow): { label: string; tone: string }[] => {
  if (isSuggestionRecord(entry)) {
    return [
      {
        label: String(entry.occurrence_count),
        tone: 'theme-pill-accent',
      },
      {
        label: entry.status,
        tone:
          entry.status === 'accepted'
            ? 'theme-pill-success'
            : entry.status === 'rejected'
              ? 'theme-pill-danger'
              : 'theme-pill-neutral',
      },
    ];
  }

  if ('symbol_type' in entry) {
    return [
      {
        label: String(entry.linked_card_count ?? 0),
        tone: 'theme-pill-accent',
      },
      {
        label: entry.symbol_type || 'symbol',
        tone: 'theme-pill-symbol',
      },
    ];
  }

  return [
    {
      label: String(entry.linked_card_count ?? 0),
      tone: 'theme-pill-accent',
    },
    {
      label: `${entry.identifiers.length} identifiers`,
      tone: metadataToneForKind(props.selectedKind),
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
