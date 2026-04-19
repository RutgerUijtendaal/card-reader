<template>
  <div v-if="kind === 'symbols'" class="grid gap-4 lg:grid-cols-2">
    <div class="space-y-3">
      <label class="field-label">
        Label
        <input v-model="entry.label" class="input-base" />
      </label>
      <label class="field-label">
        Key (optional)
        <input v-model="entry.key" class="input-base" />
      </label>
      <label class="field-label">
        Text token
        <input v-model="entry.text_token" class="input-base" placeholder="{DEVOTION}" />
      </label>
      <label class="field-label">
        Symbol type
        <input v-model="entry.symbol_type" class="input-base" placeholder="mana" />
      </label>
      <label class="field-label">
        Detector type
        <select v-model="entry.detector_type" class="input-base">
          <option
            v-for="option in detectorTypeOptions"
            :key="option.value"
            :value="option.value"
          >
            {{ option.label }}
          </option>
        </select>
      </label>
      <label class="inline-flex items-center gap-2 text-sm text-slate-700">
        <input v-model="entry.enabled" type="checkbox" />
        <span>Enabled</span>
      </label>
    </div>

    <div v-if="entry.detector_type === 'template'" class="space-y-3">
      <button
        v-if="showAdvancedToggle"
        class="btn-secondary w-fit"
        type="button"
        @click="emit('toggle-advanced')"
      >
        {{ advancedOpen ? 'Hide Config' : 'Show Config' }}
      </button>

      <template v-if="advancedOpen">
        <label class="field-label">
          Detection config JSON
          <textarea
            v-model="entry.detection_config_json"
            class="input-base min-h-24 font-mono"
            :placeholder="detectionConfigExample"
          />
          <span class="text-xs text-slate-500"> Example: {{ detectionConfigExample }} </span>
        </label>
        <label class="field-label">
          Reference assets JSON
          <textarea
            v-model="entry.reference_assets_json"
            class="input-base min-h-24 font-mono"
            :placeholder="referenceAssetsExample"
          />
          <span class="text-xs text-slate-500"> Example: {{ referenceAssetsExample }} </span>
          <button
            class="btn-secondary mt-2 w-fit"
            type="button"
            :disabled="uploadingAsset"
            @click="emit('upload-asset')"
          >
            {{ uploadingAsset ? 'Uploading...' : 'Add Asset From File' }}
          </button>
        </label>
      </template>
    </div>
  </div>

  <div v-else class="space-y-3">
    <div class="grid gap-3 md:grid-cols-2">
      <label class="field-label">
        Label
        <input v-model="entry.label" class="input-base" />
      </label>
      <label class="field-label">
        Key (optional)
        <input v-model="entry.key" class="input-base" />
      </label>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CatalogFormEntry, CatalogKind } from '@/modules/settings/types';
import type { SymbolDetectorOption } from '@/modules/settings/types';

defineProps<{
  kind: CatalogKind;
  entry: CatalogFormEntry;
  advancedOpen: boolean;
  showAdvancedToggle: boolean;
  detectorTypeOptions: SymbolDetectorOption[];
  uploadingAsset: boolean;
  detectionConfigExample: string;
  referenceAssetsExample: string;
}>();

const emit = defineEmits<{
  (e: 'toggle-advanced'): void;
  (e: 'upload-asset'): void;
}>();
</script>
