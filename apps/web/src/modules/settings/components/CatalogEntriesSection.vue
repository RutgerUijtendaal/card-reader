<template>
  <div class="rounded-lg border border-slate-200 p-3">
    <h4 class="mb-3 text-sm font-semibold text-slate-800">
      Existing {{ kindLabel(selectedKind).toLowerCase() }}
    </h4>

    <div
      v-if="currentRows.length === 0"
      class="text-sm text-slate-500"
    >
      No entries.
    </div>

    <div
      v-else
      class="space-y-3"
    >
      <div class="space-y-3 xl:hidden">
        <article
          v-for="entry in currentRows"
          :key="entry.id"
          class="rounded-lg border border-slate-200 p-3"
        >
          <CatalogEntryForm
            :kind="selectedKind"
            :entry="entry as CatalogFormEntry"
            :advanced-open="isEntryAdvancedOpen(entry.id)"
            :show-advanced-toggle="true"
            :detector-type-options="detectorTypeOptions"
            :uploading-asset="uploadingEntryAssetIds.has(entry.id)"
            :detection-config-example="detectionConfigExample"
            :reference-assets-example="referenceAssetsExample"
            @update:entry="emit('replace-entry', selectedKind, entry.id, $event)"
            @toggle-advanced="emit('toggle-advanced', entry.id)"
            @upload-asset="emit('upload-entry-asset', entry as SymbolRecord)"
          />
          <div class="mt-3 flex gap-2">
            <button
              class="btn-secondary flex-1"
              type="button"
              :disabled="savingEntryIds.has(entry.id)"
              @click="emit('save', entry)"
            >
              {{ savingEntryIds.has(entry.id) ? 'Saving...' : 'Save' }}
            </button>
            <button
              class="rounded-md border border-rose-300 px-3 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
              type="button"
              :disabled="deletingEntryIds.has(entry.id)"
              @click="emit('request-delete', entry)"
            >
              {{ deletingEntryIds.has(entry.id) ? 'Deleting...' : 'Delete' }}
            </button>
          </div>
        </article>
      </div>

      <div class="hidden overflow-x-auto xl:block">
        <table class="w-full min-w-[980px] table-fixed border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-200 text-left text-slate-600">
              <th class="px-2 py-2 font-semibold">
                Label
              </th>
              <th class="px-2 py-2 font-semibold">
                Key
              </th>
              <th
                v-if="selectedKind === 'keywords'"
                class="px-2 py-2 font-semibold"
              >
                Identifiers
              </th>
              <th
                v-if="selectedKind === 'symbols'"
                class="px-2 py-2 font-semibold"
              >
                Type
              </th>
              <th
                v-if="selectedKind === 'symbols'"
                class="px-2 py-2 font-semibold"
              >
                Text Token
              </th>
              <th
                v-if="selectedKind === 'symbols'"
                class="px-2 py-2 font-semibold"
              >
                Detector
              </th>
              <th
                v-if="selectedKind === 'symbols'"
                class="px-2 py-2 font-semibold"
              >
                Enabled
              </th>
              <th class="w-72 px-2 py-2 font-semibold">
                Action
              </th>
            </tr>
          </thead>
          <tbody>
            <template
              v-for="entry in currentRows"
              :key="entry.id"
            >
              <tr class="border-b border-slate-100 align-middle">
                <td class="px-2 py-2">
                  <input
                    v-model="entry.label"
                    class="input-base"
                  >
                </td>
                <td class="px-2 py-2">
                  <input
                    v-model="entry.key"
                    class="input-base"
                  >
                </td>
                <td
                  v-if="selectedKind === 'keywords'"
                  class="px-2 py-2"
                >
                  <textarea
                    v-model="(entry as KeywordRecord).identifiers_text"
                    class="input-base min-h-24 font-mono"
                    placeholder="turn start&#10;at the beginning of your turn"
                  />
                </td>
                <td
                  v-if="selectedKind === 'symbols'"
                  class="px-2 py-2"
                >
                  <input
                    v-model="(entry as SymbolRecord).symbol_type"
                    class="input-base"
                  >
                </td>
                <td
                  v-if="selectedKind === 'symbols'"
                  class="px-2 py-2"
                >
                  <input
                    v-model="(entry as SymbolRecord).text_token"
                    class="input-base"
                  >
                </td>
                <td
                  v-if="selectedKind === 'symbols'"
                  class="px-2 py-2"
                >
                  <select
                    v-model="(entry as SymbolRecord).detector_type"
                    class="input-base"
                  >
                    <option
                      v-for="option in detectorTypeOptions"
                      :key="option.value"
                      :value="option.value"
                    >
                      {{ option.label }}
                    </option>
                  </select>
                </td>
                <td
                  v-if="selectedKind === 'symbols'"
                  class="px-2 py-2 align-middle"
                >
                  <label class="inline-flex items-center gap-2">
                    <input
                      v-model="(entry as SymbolRecord).enabled"
                      type="checkbox"
                    >
                    <span class="text-xs text-slate-600">On</span>
                  </label>
                </td>
                <td class="px-2 py-2 align-middle">
                  <div class="flex items-center gap-2">
                    <button
                      v-if="
                        selectedKind === 'symbols' &&
                          (entry as SymbolRecord).detector_type === 'template'
                      "
                      class="btn-secondary h-10"
                      type="button"
                      @click="emit('toggle-advanced', entry.id)"
                    >
                      <span>Advanced</span>
                      <ChevronDown
                        v-if="!isEntryAdvancedOpen(entry.id)"
                        class="pl-1 h-4 w-4"
                      />
                      <ChevronUp
                        v-if="isEntryAdvancedOpen(entry.id)"
                        class="pl-1 h-4 w-4"
                      />
                    </button>
                    <button
                      class="btn-secondary h-10 flex-1"
                      type="button"
                      :disabled="savingEntryIds.has(entry.id)"
                      @click="emit('save', entry)"
                    >
                      {{ savingEntryIds.has(entry.id) ? 'Saving...' : 'Save' }}
                    </button>
                    <button
                      class="h-10 rounded-md border border-rose-300 px-3 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
                      type="button"
                      :disabled="deletingEntryIds.has(entry.id)"
                      @click="emit('request-delete', entry)"
                    >
                      {{ deletingEntryIds.has(entry.id) ? 'Deleting...' : 'Delete' }}
                    </button>
                  </div>
                </td>
              </tr>

              <tr
                v-show="
                  selectedKind === 'symbols' &&
                    (entry as SymbolRecord).detector_type === 'template' &&
                    isEntryAdvancedOpen(entry.id)
                "
                class="border-b border-slate-100"
              >
                <td
                  colspan="7"
                  class="px-2 pb-3"
                >
                  <div class="grid gap-2 md:grid-cols-2">
                    <div class="space-y-2">
                      <label class="field-label">
                        Reference assets JSON
                        <textarea
                          v-model="(entry as SymbolRecord).reference_assets_json"
                          class="input-base min-h-24 font-mono"
                          :placeholder="referenceAssetsExample"
                        />
                      </label>
                      <button
                        class="btn-secondary w-fit"
                        type="button"
                        :disabled="uploadingEntryAssetIds.has(entry.id)"
                        @click="emit('upload-entry-asset', entry as SymbolRecord)"
                      >
                        {{
                          uploadingEntryAssetIds.has(entry.id)
                            ? 'Uploading...'
                            : 'Add Asset From File'
                        }}
                      </button>
                    </div>
                    <div>
                      <label
                        v-if="(entry as SymbolRecord).detector_type === 'template'"
                        class="field-label"
                      >
                        Detection config JSON
                        <textarea
                          v-model="(entry as SymbolRecord).detection_config_json"
                          class="input-base min-h-24 font-mono"
                          :placeholder="detectionConfigExample"
                        />
                      </label>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import CatalogEntryForm from '@/modules/settings/components/CatalogEntryForm.vue';
import { ChevronUp, ChevronDown } from 'lucide-vue-next';
import type {
  CatalogFormEntry,
  CatalogKind,
  CatalogRow,
  KeywordRecord,
  SymbolDetectorOption,
  SymbolRecord,
} from '@/modules/settings/types';

defineProps<{
  selectedKind: CatalogKind;
  currentRows: CatalogRow[];
  kindLabel: (kind: CatalogKind) => string;
  savingEntryIds: Set<string>;
  deletingEntryIds: Set<string>;
  uploadingEntryAssetIds: Set<string>;
  detectorTypeOptions: SymbolDetectorOption[];
  detectionConfigExample: string;
  referenceAssetsExample: string;
  isEntryAdvancedOpen: (entryId: string) => boolean;
}>();

const emit = defineEmits<{
  (e: 'save', entry: CatalogRow): void;
  (e: 'request-delete', entry: CatalogRow): void;
  (e: 'upload-entry-asset', entry: SymbolRecord): void;
  (e: 'toggle-advanced', entryId: string): void;
  (e: 'replace-entry', kind: CatalogKind, entryId: string, next: CatalogFormEntry): void;
}>();
</script>
