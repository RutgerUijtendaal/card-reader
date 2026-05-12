<template>
  <div class="page-card flex h-full min-h-0 flex-col">
    <div class="flex items-start justify-between gap-3">
      <div>
        <h3 class="text-lg font-semibold text-slate-900">
          Version Editor
        </h3>
        <p class="text-sm text-slate-500">
          {{
            version.editable
              ? 'Manual saves lock edited fields and metadata groups against future reparses.'
              : 'Only the latest version can be edited. Historical versions remain read-only snapshots.'
          }}
        </p>
      </div>
      <span
        class="rounded-full px-2.5 py-1 text-xs font-medium"
        :class="version.editable ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'"
      >
        {{ version.editable ? 'Latest Version' : 'Historical Version' }}
      </span>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto pr-1 pt-5">
      <div class="space-y-4">
        <div
          v-for="field in scalarFields"
          :key="field.name"
          class="rounded-xl border border-slate-200 p-3"
        >
          <div class="mb-2 flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-slate-900">
                {{ field.label }}
              </p>
              <p class="text-xs text-slate-500">
                Source: {{ fieldSourceLabel(field.name) }}
              </p>
            </div>
            <div class="flex items-center gap-2">
              <button
                class="btn-secondary h-9"
                type="button"
                :disabled="!version.editable || isBusy"
                @click="$emit('restore-field', field.name)"
              >
                Reset to Parsed
              </button>
              <button
                class="btn-secondary h-9"
                type="button"
                :disabled="!version.editable || isBusy || fieldSource(field.name) === 'auto'"
                @click="$emit('unlock-field', field.name)"
              >
                Unlock for Reparse
              </button>
            </div>
          </div>

          <textarea
            v-if="field.multiline"
            :value="form[field.name]"
            class="input-base min-h-32"
            :disabled="!version.editable || isBusy"
            @input="$emit('update-field', field.name, ($event.target as HTMLTextAreaElement).value)"
          />
          <input
            v-else
            :value="form[field.name]"
            class="input-base"
            :disabled="!version.editable || isBusy"
            @input="$emit('update-field', field.name, ($event.target as HTMLInputElement).value)"
          >

          <p
            v-if="fieldHasParsedSuggestion(field.name)"
            class="mt-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600"
          >
            <span class="font-semibold text-slate-700">Parser suggestion:</span>
            {{ formatParsedFieldValue(field.name) }}
          </p>
        </div>

        <div
          v-for="group in metadataGroups"
          :key="group.name"
          class="rounded-xl border border-slate-200 p-3"
        >
          <div class="mb-3 flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-slate-900">
                {{ group.label }}
              </p>
              <p class="text-xs text-slate-500">
                Source: {{ metadataSourceLabel(group.name) }}
              </p>
            </div>
            <div class="flex items-center gap-2">
              <button
                class="btn-secondary h-9"
                type="button"
                :disabled="!version.editable || isBusy"
                @click="$emit('restore-group', group.name)"
              >
                Reset to Parsed
              </button>
              <button
                class="btn-secondary h-9"
                type="button"
                :disabled="!version.editable || isBusy || metadataSource(group.name) === 'auto'"
                @click="$emit('unlock-group', group.name)"
              >
                Unlock for Reparse
              </button>
            </div>
          </div>

          <div class="grid gap-2 sm:grid-cols-2">
            <label
              v-for="option in optionsForGroup(group.name)"
              :key="option.id"
              class="flex items-start gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700"
            >
              <input
                :checked="selectedIds(group.name).includes(option.id)"
                type="checkbox"
                :disabled="!version.editable || isBusy"
                @change="$emit('toggle-group', group.name, option.id, ($event.target as HTMLInputElement).checked)"
              >
              <span>{{ option.label }}</span>
            </label>
          </div>

          <p
            v-if="metadataHasParsedSuggestion(group.name)"
            class="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600"
          >
            <span class="font-semibold text-slate-700">Parser suggestion:</span>
            {{ parsedMetadataLabels(group.name).join(', ') || 'None' }}
          </p>
        </div>
      </div>
    </div>

    <div class="flex shrink-0 items-center justify-end gap-3 border-t border-slate-200 bg-white pt-4">
      <p
        v-if="saveMessage"
        class="mr-auto text-sm text-emerald-700"
      >
        {{ saveMessage }}
      </p>
      <button
        class="btn-secondary"
        type="button"
        :disabled="!version.editable || isBusy"
        @click="$emit('reset-whole-card')"
      >
        Reset Whole Card to Auto
      </button>
      <button
        class="btn-secondary"
        type="button"
        :disabled="!version.editable || isBusy"
        @click="$emit('queue-reparse')"
      >
        {{ isQueuingReparse ? 'Queueing Reparse...' : 'Queue Reparse' }}
      </button>
      <button
        class="btn-primary"
        type="button"
        :disabled="!version.editable || isBusy"
        @click="$emit('save')"
      >
        {{ isSaving ? 'Saving...' : 'Save Edits' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type {
  CardVersionDetail,
  EditorForm,
  MetadataGroupName,
  MetadataOption,
  ScalarFieldName,
  SymbolFilterOption,
} from '@/modules/card-detail/types';
import { metadataGroups, scalarFields } from '@/modules/card-detail/types';

defineProps<{
  version: CardVersionDetail;
  form: EditorForm;
  isBusy: boolean;
  isSaving: boolean;
  isQueuingReparse: boolean;
  saveMessage: string;
  fieldSource: (fieldName: ScalarFieldName) => 'auto' | 'manual';
  metadataSource: (groupName: MetadataGroupName) => 'auto' | 'manual';
  fieldSourceLabel: (fieldName: ScalarFieldName) => string;
  metadataSourceLabel: (groupName: MetadataGroupName) => string;
  fieldHasParsedSuggestion: (fieldName: ScalarFieldName) => boolean;
  formatParsedFieldValue: (fieldName: ScalarFieldName) => string;
  metadataHasParsedSuggestion: (groupName: MetadataGroupName) => boolean;
  selectedIds: (groupName: MetadataGroupName) => string[];
  parsedMetadataLabels: (groupName: MetadataGroupName) => string[];
  optionsForGroup: (groupName: MetadataGroupName) => Array<MetadataOption | SymbolFilterOption>;
}>();

defineEmits<{
  (e: 'save'): void;
  (e: 'restore-field', fieldName: ScalarFieldName): void;
  (e: 'unlock-field', fieldName: ScalarFieldName): void;
  (e: 'restore-group', groupName: MetadataGroupName): void;
  (e: 'unlock-group', groupName: MetadataGroupName): void;
  (e: 'reset-whole-card'): void;
  (e: 'queue-reparse'): void;
  (e: 'toggle-group', groupName: MetadataGroupName, optionId: string, checked: boolean): void;
  (e: 'update-field', fieldName: ScalarFieldName, value: string): void;
}>();
</script>
