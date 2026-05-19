<template>
  <section class="flex min-h-0 flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <div class="flex flex-col gap-4 border-b border-slate-200 pb-4 md:flex-row md:items-start md:justify-between">
      <div>
        <p class="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
          Review {{ kindItemLabel(selectedKind) }}
        </p>
        <h4 class="mt-2 text-lg font-semibold text-slate-900">
          {{ selectedRow?.display_value || 'Select a suggestion' }}
        </h4>
        <p
          v-if="selectedRow"
          class="mt-2 text-sm text-slate-500"
        >
          {{ selectedRow.occurrence_count }} matches • {{ selectedRow.status }}
        </p>
      </div>

      <div
        v-if="selectedRow"
        class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600"
      >
        <div class="font-semibold text-slate-700">
          Suggested value
        </div>
        <div class="mt-1">
          Key: <span class="font-mono text-[11px]">{{ selectedRow.normalized_value }}</span>
        </div>
      </div>
    </div>

    <div
      v-if="!selectedRow"
      class="py-8 text-sm text-slate-500"
    >
      Select a suggestion to review it.
    </div>

    <div
      v-else
      class="app-scrollbar mt-5 min-h-0 flex-1 space-y-5 overflow-y-auto pr-1"
    >
      <div class="grid gap-5 xl:grid-cols-2">
        <div class="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
          <div class="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
            Accept as existing
          </div>
          <div class="mt-3 flex flex-col gap-3">
            <label class="field-label">
              Existing {{ selectedKind === 'suggested-tags' ? 'tag' : 'type' }}
              <select
                v-model="existingTargetIdModel"
                class="input-base"
              >
                <option value="">
                  Select existing {{ selectedKind === 'suggested-tags' ? 'tag' : 'type' }}
                </option>
                <option
                  v-for="option in existingOptions"
                  :key="option.id"
                  :value="option.id"
                >
                  {{ option.label }} ({{ option.key }})
                </option>
              </select>
            </label>
            <button
              class="btn-primary w-fit"
              type="button"
              :disabled="!existingTargetIdModel || actionLoading"
              @click="emit('accept-existing', existingTargetIdModel)"
            >
              {{ actionLoading ? 'Saving...' : 'Accept as Existing' }}
            </button>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
          <div class="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
            Accept as new
          </div>
          <div class="mt-3 grid gap-3 md:grid-cols-2">
            <label class="field-label">
              Label
              <input
                v-model="newLabelModel"
                class="input-base"
              >
            </label>
            <label class="field-label">
              Key (optional)
              <input
                v-model="newKeyModel"
                class="input-base"
              >
            </label>
          </div>
          <button
            class="btn-primary mt-3 w-fit"
            type="button"
            :disabled="actionLoading"
            @click="emit('accept-new', { label: newLabelModel, key: newKeyModel })"
          >
            {{ actionLoading ? 'Saving...' : 'Create and Accept' }}
          </button>
        </div>
      </div>

      <div class="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
              Linked cards
            </div>
            <div class="mt-1 text-sm text-slate-500">
              {{ selectedRow.occurrence_count }} cards where this suggestion was found.
            </div>
          </div>
          <button
            class="rounded-lg border border-amber-300 px-4 py-2 text-sm font-semibold text-amber-700 transition hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            :disabled="actionLoading || selectedRow.status === 'rejected'"
            @click="emit('reject')"
          >
            {{ actionLoading ? 'Saving...' : 'Reject' }}
          </button>
        </div>

        <div class="mt-4">
          <CatalogLinkedCardsGrid
            :cards="selectedRow.occurrences"
            empty-message="No linked cards found for this suggestion."
          />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import CatalogLinkedCardsGrid from '@/modules/settings/components/CatalogLinkedCardsGrid.vue';
import type {
  CatalogKind,
  SuggestionAcceptNewRequest,
  SuggestionRecord,
  TagRecord,
  TypeRecord,
} from '@/modules/settings/types';

const props = defineProps<{
  selectedKind: CatalogKind;
  selectedRow: SuggestionRecord | null;
  existingOptions: TagRecord[] | TypeRecord[];
  existingTargetId: string;
  newLabel: string;
  newKey: string;
  actionLoading: boolean;
  kindItemLabel: (kind: CatalogKind) => string;
}>();

const emit = defineEmits<{
  (e: 'update:existing-target-id', value: string): void;
  (e: 'update:new-label', value: string): void;
  (e: 'update:new-key', value: string): void;
  (e: 'accept-existing', targetId: string): void;
  (e: 'accept-new', payload: SuggestionAcceptNewRequest): void;
  (e: 'reject'): void;
}>();

const existingTargetIdModel = computed({
  get: () => props.existingTargetId,
  set: (value: string) => emit('update:existing-target-id', value),
});

const newLabelModel = computed({
  get: () => props.newLabel,
  set: (value: string) => emit('update:new-label', value),
});

const newKeyModel = computed({
  get: () => props.newKey,
  set: (value: string) => emit('update:new-key', value),
});
</script>
