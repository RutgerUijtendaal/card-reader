<template>
  <div
    v-if="kind === 'symbols'"
    class="grid gap-4 lg:grid-cols-2"
  >
    <div class="space-y-3">
      <label class="field-label">
        Label
        <input
          v-model="labelModel"
          class="input-base"
        >
      </label>
      <label class="field-label">
        Key (optional)
        <input
          v-model="keyModel"
          class="input-base"
        >
      </label>
      <label class="field-label">
        Text token
        <input
          v-model="textTokenModel"
          class="input-base"
          placeholder="{DEVOTION}"
        >
      </label>
      <label class="field-label">
        Symbol type
        <input
          v-model="symbolTypeModel"
          class="input-base"
          placeholder="mana"
        >
      </label>
      <label class="field-label">
        Detector type
        <select
          v-model="detectorTypeModel"
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
      </label>
      <label class="inline-flex items-center gap-2 text-sm text-slate-700">
        <input
          v-model="enabledModel"
          type="checkbox"
        >
        <span>Enabled</span>
      </label>
    </div>

    <div
      v-if="entry.detector_type === 'template'"
      class="space-y-3"
    >
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
            v-model="detectionConfigModel"
            class="input-base min-h-24 font-mono"
            :placeholder="detectionConfigExample"
          />
        </label>
        <label class="field-label">
          Text enrichment JSON
          <textarea
            v-model="textEnrichmentModel"
            class="input-base min-h-24 font-mono"
            placeholder="{&quot;ocr_aliases&quot;:[],&quot;pattern_anchors&quot;:[]}"
          />
          <span class="text-xs font-normal text-slate-500">
            Define OCR aliases and literal anchor matches used to insert this symbol into rule text.
          </span>
        </label>
        <label class="field-label">
          Reference assets JSON
          <textarea
            v-model="referenceAssetsModel"
            class="input-base min-h-24 font-mono"
            :placeholder="referenceAssetsExample"
          />
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

  <div
    v-else
    class="space-y-3"
  >
    <div class="grid gap-3 md:grid-cols-2">
      <label class="field-label">
        Label
        <input
          v-model="labelModel"
          class="input-base"
        >
      </label>
      <label class="field-label">
        Key (optional)
        <input
          v-model="keyModel"
          class="input-base"
        >
      </label>
    </div>
    <label class="field-label">
      Identifiers
      <textarea
        v-model="identifiersTextModel"
        class="input-base min-h-24 font-mono"
        placeholder="turn start&#10;at the beginning of your turn"
      />
      <span class="text-xs font-normal text-slate-500">
        One identifier per line. Matching is case-insensitive.
      </span>
    </label>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { CatalogFormEntry, CatalogKind } from '@/modules/settings/types';
import type { SymbolDetectorOption } from '@/modules/settings/types';

const props = defineProps<{
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
  (e: 'update:entry', entry: CatalogFormEntry): void;
}>();

const updateEntry = (patch: Partial<CatalogFormEntry>): void => {
  emit('update:entry', { ...props.entry, ...patch });
};

const labelModel = computed({
  get: () => props.entry.label,
  set: (value: string) => updateEntry({ label: value }),
});

const keyModel = computed({
  get: () => props.entry.key,
  set: (value: string) => updateEntry({ key: value }),
});

const identifiersTextModel = computed({
  get: () => props.entry.identifiers_text ?? '',
  set: (value: string) => updateEntry({ identifiers_text: value }),
});

const textTokenModel = computed({
  get: () => props.entry.text_token,
  set: (value: string) => updateEntry({ text_token: value }),
});

const symbolTypeModel = computed({
  get: () => props.entry.symbol_type,
  set: (value: string) => updateEntry({ symbol_type: value }),
});

const detectorTypeModel = computed({
  get: () => props.entry.detector_type,
  set: (value: CatalogFormEntry['detector_type']) => updateEntry({ detector_type: value }),
});

const enabledModel = computed({
  get: () => props.entry.enabled,
  set: (value: boolean) => updateEntry({ enabled: value }),
});

const detectionConfigModel = computed({
  get: () => props.entry.detection_config_json,
  set: (value: string) => updateEntry({ detection_config_json: value }),
});

const textEnrichmentModel = computed({
  get: () => props.entry.text_enrichment_json,
  set: (value: string) => updateEntry({ text_enrichment_json: value }),
});

const referenceAssetsModel = computed({
  get: () => props.entry.reference_assets_json,
  set: (value: string) => updateEntry({ reference_assets_json: value }),
});
</script>
