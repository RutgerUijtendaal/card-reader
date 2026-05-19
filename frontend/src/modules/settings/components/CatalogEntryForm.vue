<template>
  <div
    v-if="kind === 'symbols'"
    class="grid gap-4 xl:grid-cols-2"
  >
    <div class="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
      <div class="grid gap-3">
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
            :class="keyDisabled ? 'cursor-not-allowed border-dashed border-slate-300 bg-slate-100 text-slate-500' : ''"
            :disabled="keyDisabled"
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
        <label class="inline-flex items-center gap-2 text-sm text-slate-700">
          <input
            v-model="enabledModel"
            type="checkbox"
          >
          <span>Enabled</span>
        </label>
      </div>
    </div>

    <template v-if="entry.detector_type === 'template' && advancedOpen">
      <div class="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
        <JsonEditorField
          v-model="detectionConfigModel"
          label="Detection config JSON"
          hint="Configure detection thresholds and matching behavior for this symbol."
          example-title="Detection config example"
          :example-json="formattedDetectionConfigExample"
          min-height="14rem"
        />
      </div>

      <div class="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
        <JsonEditorField
          v-model="textEnrichmentModel"
          label="Text enrichment JSON"
          hint="Define OCR aliases and anchor matches used when inserting this symbol into normalized text."
          example-title="Text enrichment example"
          :example-json="textEnrichmentExample"
          min-height="14rem"
        />
      </div>

      <div class="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
        <div class="space-y-2">
          <JsonEditorField
            v-model="referenceAssetsModel"
            label="Reference assets JSON"
            hint="List the asset paths used as visual references for this symbol."
            example-title="Reference assets example"
            :example-json="formattedReferenceAssetsExample"
            min-height="14rem"
          />
          <button
            class="btn-secondary w-fit"
            type="button"
            :disabled="uploadingAsset"
            @click="emit('upload-asset')"
          >
            {{ uploadingAsset ? 'Uploading...' : 'Add Asset From File' }}
          </button>
        </div>
      </div>
    </template>
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
          :class="keyDisabled ? 'cursor-not-allowed border-dashed border-slate-300 bg-slate-100 text-slate-500' : ''"
          :disabled="keyDisabled"
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
import JsonEditorField from '@/modules/settings/components/JsonEditorField.vue';
import type { CatalogFormEntry, CatalogKind } from '@/modules/settings/types';
import { textEnrichmentExample } from '@/modules/settings/composables/catalogSettingsUtils';

const props = defineProps<{
  kind: CatalogKind;
  entry: CatalogFormEntry;
  advancedOpen: boolean;
  showAdvancedToggle: boolean;
  keyDisabled?: boolean;
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

const formattedDetectionConfigExample = computed(() =>
  JSON.stringify(JSON.parse(props.detectionConfigExample), null, 2),
);

const formattedReferenceAssetsExample = computed(() =>
  JSON.stringify(JSON.parse(props.referenceAssetsExample), null, 2),
);

</script>
