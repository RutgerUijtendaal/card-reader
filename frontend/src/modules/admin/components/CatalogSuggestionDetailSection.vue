<template>
  <section class="theme-panel-shell flex min-h-0 flex-col rounded-2xl p-5 shadow-sm">
    <div class="theme-divider flex flex-col gap-4 border-b pb-4 md:flex-row md:items-start md:justify-between">
      <div>
        <p class="theme-kicker text-xs font-medium uppercase tracking-[0.18em]">
          Review {{ kindItemLabel(selectedKind) }}
        </p>
        <h4 class="theme-section-title mt-2 text-lg font-semibold">
          {{ selectedRow?.display_value || 'Select a suggestion' }}
        </h4>
        <p
          v-if="selectedRow"
          class="theme-section-muted mt-2 text-sm"
        >
          {{ selectedRow.occurrence_count }} matches • {{ selectedRow.status }}
        </p>
      </div>

      <div
        v-if="selectedRow"
        class="theme-info-box text-xs"
      >
        <div class="theme-section-title font-semibold">
          Suggested value
        </div>
        <div class="mt-1">
          Key: <span class="font-mono text-[11px]">{{ selectedRow.normalized_value }}</span>
        </div>
      </div>
    </div>

    <div
      v-if="!selectedRow"
      class="theme-section-muted py-8 text-sm"
    >
      Select a suggestion to review it.
    </div>

    <div
      v-else
      class="app-scrollbar mt-5 min-h-0 flex-1 space-y-5 overflow-y-auto pr-1"
    >
      <div class="grid gap-5 xl:grid-cols-2">
        <div class="theme-muted-panel">
          <div class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]">
            Accept as existing
          </div>
          <div class="mt-3 flex flex-col gap-3">
            <label class="field-label">
              Existing {{ selectedKind === 'suggested-tags' ? 'tag' : 'type' }}
              <AppSelect
                v-model="existingTargetIdModel"
                :options="existingSelectOptions"
                :placeholder="`Select existing ${selectedKind === 'suggested-tags' ? 'tag' : 'type'}`"
              />
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

        <div class="theme-muted-panel">
          <div class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]">
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

      <div class="theme-muted-panel">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]">
              Linked cards
            </div>
            <div class="theme-section-muted mt-1 text-sm">
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
import AppSelect from '@/components/app/AppSelect.vue';
import CatalogLinkedCardsGrid from '@/modules/admin/components/CatalogLinkedCardsGrid.vue';
import type {
  CatalogKind,
  SuggestionAcceptNewRequest,
  SuggestionRecord,
  TagRecord,
  TypeRecord,
} from '@/modules/admin/types';

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
const existingSelectOptions = computed(() =>
  props.existingOptions.map((option) => ({
    value: option.id,
    label: `${option.label} (${option.key})`,
  })),
);

const newLabelModel = computed({
  get: () => props.newLabel,
  set: (value: string) => emit('update:new-label', value),
});

const newKeyModel = computed({
  get: () => props.newKey,
  set: (value: string) => emit('update:new-key', value),
});
</script>
