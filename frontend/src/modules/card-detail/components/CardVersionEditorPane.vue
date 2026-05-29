<template>
  <div class="page-card flex h-full min-h-0 flex-col">
    <div class="flex items-start justify-between gap-3">
      <div>
        <h3 class="theme-section-title text-lg font-semibold">
          Version Editor
        </h3>
        <p class="theme-section-muted text-sm">
          {{
            version.editable
              ? 'Manual saves lock edited fields and metadata groups against future reparses.'
              : 'Only the latest version can be edited. Historical versions remain read-only snapshots.'
          }}
        </p>
      </div>
      <span
        class="theme-pill px-2.5 py-1 text-xs"
        :class="version.editable ? 'theme-pill-success' : 'theme-pill-neutral'"
      >
        {{ version.editable ? 'Latest Version' : 'Historical Version' }}
      </span>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto pr-1 pt-5">
      <div class="space-y-4">
        <div class="theme-muted-panel p-3">
          <div class="flex flex-wrap items-center justify-between gap-4">
            <div class="min-w-0">
              <p class="theme-section-title text-sm font-semibold">
                Hero Card
              </p>
              <p class="theme-section-muted text-xs">
                Manual card-level deckbuilding flag.
              </p>
            </div>

            <label class="theme-section-title flex shrink-0 items-center gap-3 text-sm font-semibold">
              <input
                :checked="form.is_hero"
                type="checkbox"
                class="theme-checkbox h-4 w-4"
                :disabled="!version.editable || isBusy"
                @change="$emit('update-hero', ($event.target as HTMLInputElement).checked)"
              >
              <span>{{ form.is_hero ? 'Marked as hero' : 'Not marked as hero' }}</span>
            </label>
          </div>
        </div>

        <div class="theme-muted-panel p-3">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div class="min-w-0">
              <p class="theme-section-title text-sm font-semibold">
                Card Status
              </p>
              <p class="theme-section-muted text-xs">
                Deprecated cards stay stored but are hidden from normal play views.
              </p>
            </div>

            <div class="grid min-w-52 grid-cols-2 gap-2">
              <button
                v-for="option in lifecycleOptions"
                :key="option.value"
                class="theme-pill justify-center px-3 py-2 text-xs font-semibold"
                :class="form.lifecycle_status === option.value ? 'theme-pill-accent' : 'theme-pill-neutral'"
                type="button"
                :disabled="lifecycleOptionDisabled(option.value)"
                :title="lifecycleOptionTitle(option.value)"
                :data-testid="`lifecycle-option-${option.value}`"
                @click="$emit('update-lifecycle-status', option.value)"
              >
                {{ option.label }}
              </button>
            </div>
          </div>
          <p
            v-if="deprecatedStatusDisabled"
            class="theme-section-muted mt-3 text-xs"
          >
            Group anchors must stay active. Choose a different anchor before deprecating this card.
          </p>
        </div>

        <div
          v-for="field in scalarFields"
          :key="field.name"
          class="theme-muted-panel p-3"
        >
          <div class="mb-2 flex items-center justify-between gap-3">
            <div>
              <p class="theme-section-title text-sm font-semibold">
                {{ field.label }}
              </p>
              <p class="theme-section-muted text-xs">
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

          <template v-if="field.name === 'rules_text'">
            <div class="mb-3 theme-card-frame-muted rounded-lg px-3 py-3 text-xs">
              <p class="theme-section-title font-semibold">
                Symbol autocomplete
              </p>
              <p class="theme-section-muted mt-2">
                Type <code>[[</code> or <code>[[symbol:</code> inside the rules text to open symbol autocomplete, then use arrow keys and Enter to insert the selected symbol.
              </p>
            </div>

            <div class="relative">
              <textarea
                ref="rulesTextTextarea"
                :value="rulesTextValue"
                class="input-base min-h-32"
                :disabled="!version.editable || isBusy"
                @input="onRulesTextInput"
                @click="syncRulesTextCaret"
                @keyup="syncRulesTextCaret"
                @select="syncRulesTextCaret"
                @keydown="onRulesTextKeydown"
              />

              <div
                v-if="showSymbolAutocomplete"
                class="theme-popover absolute left-0 right-0 top-[calc(100%+0.5rem)] z-10 p-2"
              >
                <p class="theme-kicker px-2 pb-2 text-[11px] font-medium uppercase tracking-wide">
                  Symbols
                </p>
                <div class="grid gap-1">
                  <button
                    v-for="(option, index) in filteredSymbolInsertOptions"
                    :key="`autocomplete-${option.id}`"
                    type="button"
                    class="theme-section-title flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition"
                    :class="index === activeAutocompleteIndex ? 'theme-selected-surface' : 'theme-card-frame-muted'"
                    @mousedown.prevent="applyAutocompleteOption(option.key)"
                  >
                    <SymbolToken
                      :asset-url="option.asset_url"
                      :label="option.label"
                      :text-token="option.text_token"
                      class="h-4 w-4"
                    />
                    <span class="min-w-0 flex-1 truncate">{{ option.label }}</span>
                    <span class="theme-kicker text-xs">{{ option.text_token || option.key }}</span>
                  </button>
                </div>
              </div>
            </div>

            <div
              class="mt-3 grid gap-3"
              :class="ruleTextUnknownSymbolKeys.length > 0 ? 'lg:grid-cols-2' : ''"
            >
              <div class="theme-card-frame-muted rounded-lg px-3 py-3">
                <p class="theme-section-title text-xs font-semibold uppercase tracking-wide">
                  Referenced In Rules Text
                </p>
                <div class="mt-2 flex flex-wrap gap-2">
                  <span
                    v-for="symbol in ruleTextSymbols"
                    :key="`rules-${symbol.id}`"
                    class="theme-pill theme-pill-symbol inline-flex items-center gap-2 px-2 py-1 text-xs"
                  >
                    <SymbolToken
                      :asset-url="symbol.asset_url"
                      :label="symbol.label"
                      :text-token="symbol.text_token"
                      class="h-4 w-4"
                    />
                    <span>{{ symbol.label }}</span>
                  </span>
                  <span
                    v-if="ruleTextSymbols.length === 0"
                    class="theme-kicker text-xs"
                  >
                    No linked symbols yet
                  </span>
                </div>
              </div>

              <div
                v-if="ruleTextUnknownSymbolKeys.length > 0"
                class="theme-card-frame-muted rounded-lg border border-amber-400/40 px-3 py-3"
              >
                <p class="theme-section-title text-xs font-semibold uppercase tracking-wide">
                  Unknown Placeholders
                </p>
                <p class="theme-section-muted mt-1 text-xs">
                  These keys are not in the symbol catalog and will not render as tokens.
                </p>
                <div class="mt-2 flex flex-wrap gap-2">
                  <span
                    v-for="symbolKey in ruleTextUnknownSymbolKeys"
                    :key="`unknown-${symbolKey}`"
                    class="theme-pill theme-pill-warning px-2 py-1 text-xs"
                  >
                    {{ symbolKey }}
                  </span>
                </div>
              </div>
            </div>
          </template>

          <input
            v-else
            :value="form[field.name]"
            class="input-base"
            :disabled="!version.editable || isBusy"
            @input="$emit('update-field', field.name, ($event.target as HTMLInputElement).value)"
          >

          <p
            v-if="fieldHasParsedSuggestion(field.name)"
            class="theme-card-frame-muted theme-section-muted mt-2 rounded-lg px-3 py-2 text-xs"
          >
            <span class="theme-section-title font-semibold">Parser suggestion:</span>
            {{ formatParsedFieldValue(field.name) }}
          </p>
        </div>

        <div class="theme-muted-panel p-3">
          <div class="mb-3 flex items-center justify-between gap-3">
            <div>
              <p class="theme-section-title text-sm font-semibold">
                Symbols
              </p>
              <p class="theme-section-muted text-xs">
                Source: {{ metadataSourceLabel('symbols') }}
              </p>
            </div>
            <div class="flex items-center gap-2">
              <button
                class="btn-secondary h-9"
                type="button"
                :disabled="!version.editable || isBusy"
                @click="$emit('restore-group', 'symbols')"
              >
                Reset to Parsed
              </button>
              <button
                class="btn-secondary h-9"
                type="button"
                :disabled="!version.editable || isBusy || metadataSource('symbols') === 'auto'"
                @click="$emit('unlock-group', 'symbols')"
              >
                Unlock for Reparse
              </button>
            </div>
          </div>

          <div>
            <p class="theme-section-title text-xs font-semibold uppercase tracking-wide">
              Linked Symbols
            </p>
            <p class="theme-section-muted mt-1 text-xs">
              Symbols referenced in rules text stay linked automatically. Other symbols can still be linked manually.
            </p>
            <div class="mt-3 grid gap-2 sm:grid-cols-2">
              <label
                v-for="option in symbolInsertOptions"
                :key="`symbol-${option.id}`"
                class="theme-card-frame-muted theme-section-title flex items-center gap-3 rounded-lg px-3 py-2 text-sm"
              >
                <input
                  :checked="additionalSymbolIds.includes(option.id) || rulesTextSymbolIds.includes(option.id)"
                  type="checkbox"
                  class="theme-checkbox h-4 w-4"
                  :disabled="!version.editable || isBusy || rulesTextSymbolIds.includes(option.id)"
                  @change="$emit('toggle-additional-symbol', option.id, ($event.target as HTMLInputElement).checked)"
                >
                <SymbolToken
                  :asset-url="option.asset_url"
                  :label="option.label"
                  :text-token="option.text_token"
                  class="h-4 w-4"
                />
                <span class="min-w-0 flex-1 truncate">{{ option.label }}</span>
                <span
                  v-if="rulesTextSymbolIds.includes(option.id)"
                  class="theme-pill theme-pill-neutral inline-flex items-center gap-1 px-2 py-0.5 text-[10px]"
                  title="Linked from rules text"
                >
                  <Lock class="h-3 w-3" />
                  <span>Locked</span>
                </span>
              </label>
            </div>
            <p
              v-if="symbolInsertOptions.length === 0"
              class="theme-empty-state mt-2"
            >
              No symbols match this filter.
            </p>
          </div>

          <p
            v-if="metadataHasParsedSuggestion('symbols')"
            class="theme-card-frame-muted theme-section-muted mt-3 rounded-lg px-3 py-2 text-xs"
          >
            <span class="theme-section-title font-semibold">Parser suggestion:</span>
            {{ parsedMetadataLabels('symbols').join(', ') || 'None' }}
          </p>
        </div>

        <div
          v-for="group in nonSymbolMetadataGroups"
          :key="group.name"
          class="theme-muted-panel p-3"
        >
          <div class="mb-3 flex items-center justify-between gap-3">
            <div>
              <p class="theme-section-title text-sm font-semibold">
                {{ group.label }}
              </p>
              <p class="theme-section-muted text-xs">
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

          <label class="field-label mb-3">
            Search {{ group.label.toLowerCase() }}
            <input
              :value="metadataSearch[group.name]"
              class="input-base"
              :disabled="isBusy"
              placeholder="Filter by label, key, or token"
              @input="$emit('update-group-search', group.name, ($event.target as HTMLInputElement).value)"
            >
          </label>

          <div class="grid gap-2 sm:grid-cols-2">
            <label
              v-for="option in optionsForGroup(group.name)"
              :key="option.id"
              class="theme-card-frame-muted theme-section-title flex items-center gap-3 rounded-lg px-3 py-2 text-sm"
            >
              <input
                :checked="selectedIds(group.name).includes(option.id)"
                type="checkbox"
                class="theme-checkbox h-4 w-4"
                :disabled="!version.editable || isBusy"
                @change="$emit('toggle-group', group.name, option.id, ($event.target as HTMLInputElement).checked)"
              >
              <span>{{ option.label }}</span>
            </label>
          </div>

          <p
            v-if="optionsForGroup(group.name).length === 0"
            class="theme-empty-state"
          >
            No {{ group.label.toLowerCase() }} match this filter.
          </p>

          <p
            v-if="metadataHasParsedSuggestion(group.name)"
            class="theme-card-frame-muted theme-section-muted mt-3 rounded-lg px-3 py-2 text-xs"
          >
            <span class="theme-section-title font-semibold">Parser suggestion:</span>
            {{ parsedMetadataLabels(group.name).join(', ') || 'None' }}
          </p>
        </div>
      </div>
    </div>

    <div class="theme-divider flex shrink-0 flex-wrap items-center gap-3 border-t pt-4">
      <label
        v-if="version.editable"
        class="theme-section-title mr-auto flex min-w-0 items-center gap-3 text-sm font-semibold"
      >
        <span class="shrink-0">Template</span>
        <AppSelect
          :model-value="reparseTemplateId"
          :options="reparseTemplateOptions"
          wrapper-class="min-w-48"
          :disabled="isBusy"
          @update:model-value="handleReparseTemplateChange"
        />
      </label>
      <p
        v-else-if="saveMessage"
        class="theme-success-text mr-auto text-sm"
      >
        {{ saveMessage }}
      </p>
      <p
        v-if="version.editable && saveMessage"
        class="theme-success-text text-sm"
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
import { computed, nextTick, ref, watch } from 'vue';
import { Lock } from 'lucide-vue-next';
import AppSelect from '@/components/app/AppSelect.vue';
import SymbolToken from '@/components/SymbolToken.vue';
import {
  ACTIVE_CARD_LIFECYCLE_STATUS,
  DEPRECATED_CARD_LIFECYCLE_STATUS,
  type CardLifecycleStatus,
} from '@/modules/card-filters/cardLifecycle';
import {
  applySymbolAutocomplete,
  findActiveSymbolTrigger,
} from '@/modules/card-detail/ruleTextSymbols';
import type {
  CardVersionDetail,
  EditorForm,
  MetadataGroupName,
  MetadataOption,
  MetadataSearchState,
  ReparseTemplateOption,
  ScalarFieldName,
  SymbolFilterOption,
} from '@/modules/card-detail/types';
import { metadataGroups, scalarFields } from '@/modules/card-detail/types';

const props = defineProps<{
  version: CardVersionDetail;
  form: EditorForm;
  reparseTemplates: ReparseTemplateOption[];
  reparseTemplateId: string;
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
  metadataSearch: MetadataSearchState;
  selectedIds: (groupName: MetadataGroupName) => string[];
  parsedMetadataLabels: (groupName: MetadataGroupName) => string[];
  optionsForGroup: (groupName: MetadataGroupName) => Array<MetadataOption | SymbolFilterOption>;
  ruleTextSymbols: SymbolFilterOption[];
  additionalSymbolIds: string[];
  ruleTextUnknownSymbolKeys: string[];
  deprecatedStatusDisabled?: boolean;
}>();

const emit = defineEmits<{
  (e: 'save'): void;
  (e: 'restore-field', fieldName: ScalarFieldName): void;
  (e: 'unlock-field', fieldName: ScalarFieldName): void;
  (e: 'restore-group', groupName: MetadataGroupName): void;
  (e: 'unlock-group', groupName: MetadataGroupName): void;
  (e: 'reset-whole-card'): void;
  (e: 'queue-reparse'): void;
  (e: 'update-reparse-template', templateId: string): void;
  (e: 'toggle-group', groupName: MetadataGroupName, optionId: string, checked: boolean): void;
  (e: 'toggle-additional-symbol', optionId: string, checked: boolean): void;
  (e: 'update-group-search', groupName: MetadataGroupName, value: string): void;
  (e: 'update-field', fieldName: ScalarFieldName, value: string): void;
  (e: 'update-hero', value: boolean): void;
  (e: 'update-lifecycle-status', value: CardLifecycleStatus): void;
}>();

const rulesTextTextarea = ref<HTMLTextAreaElement | null>(null);
const rulesTextValue = ref('');
const rulesTextCaretIndex = ref(0);
const activeAutocompleteIndex = ref(0);
const dismissedTriggerStart = ref<number | null>(null);
const nonSymbolMetadataGroups = metadataGroups.filter((group) => group.name !== 'symbols');
const lifecycleOptions = [
  { value: ACTIVE_CARD_LIFECYCLE_STATUS, label: 'Active' },
  { value: DEPRECATED_CARD_LIFECYCLE_STATUS, label: 'Deprecated' },
] as const;
const symbolInsertOptions = computed(() => props.optionsForGroup('symbols') as SymbolFilterOption[]);
const rulesTextSymbolIds = computed(() => props.ruleTextSymbols.map((symbol) => symbol.id));
const additionalSymbolIds = computed(() => props.additionalSymbolIds);
const reparseTemplateOptions = computed(() =>
  props.reparseTemplates.map((option) => ({
    value: option.key,
    label: option.label,
  })),
);
const activeSymbolTrigger = computed(() =>
  findActiveSymbolTrigger(rulesTextValue.value, rulesTextCaretIndex.value),
);
const filteredSymbolInsertOptions = computed(() => {
  const trigger = activeSymbolTrigger.value;
  if (!trigger) {
    return [];
  }

  const normalizedQuery = trigger.query.trim().toLowerCase();
  if (!normalizedQuery) {
    return symbolInsertOptions.value.slice(0, 8);
  }

  return symbolInsertOptions.value
    .filter((option) =>
      [option.label, option.key, option.text_token].some((value) =>
        value.toLowerCase().includes(normalizedQuery),
      ),
    )
    .slice(0, 8);
});
const showSymbolAutocomplete = computed(() => {
  const trigger = activeSymbolTrigger.value;
  if (!trigger || filteredSymbolInsertOptions.value.length === 0) {
    return false;
  }
  return dismissedTriggerStart.value !== trigger.start;
});

const lifecycleOptionDisabled = (value: CardLifecycleStatus): boolean =>
  !props.version.editable ||
  props.isBusy ||
  (value === DEPRECATED_CARD_LIFECYCLE_STATUS && props.deprecatedStatusDisabled === true);

const lifecycleOptionTitle = (value: CardLifecycleStatus): string | undefined =>
  value === DEPRECATED_CARD_LIFECYCLE_STATUS && props.deprecatedStatusDisabled === true
    ? 'Group anchors must stay active.'
    : undefined;

watch(
  () => props.form.rules_text,
  (value) => {
    rulesTextValue.value = value;
  },
  { immediate: true },
);

watch(activeSymbolTrigger, () => {
  activeAutocompleteIndex.value = 0;
});

watch(filteredSymbolInsertOptions, (options) => {
  if (options.length === 0) {
    activeAutocompleteIndex.value = 0;
    return;
  }
  activeAutocompleteIndex.value = Math.min(activeAutocompleteIndex.value, options.length - 1);
});

const onRulesTextInput = (event: Event): void => {
  const target = event.target as HTMLTextAreaElement;
  rulesTextValue.value = target.value;
  rulesTextCaretIndex.value = target.selectionStart ?? target.value.length;
  dismissedTriggerStart.value = null;
  emit('update-field', 'rules_text', target.value);
};

const syncRulesTextCaret = (event: Event): void => {
  const target = event.target as HTMLTextAreaElement;
  rulesTextCaretIndex.value = target.selectionStart ?? target.value.length;
  dismissedTriggerStart.value = null;
};

const onRulesTextKeydown = (event: KeyboardEvent): void => {
  if (!showSymbolAutocomplete.value) {
    return;
  }

  if (event.key === 'ArrowDown') {
    event.preventDefault();
    activeAutocompleteIndex.value =
      (activeAutocompleteIndex.value + 1) % filteredSymbolInsertOptions.value.length;
    return;
  }

  if (event.key === 'ArrowUp') {
    event.preventDefault();
    activeAutocompleteIndex.value =
      (activeAutocompleteIndex.value - 1 + filteredSymbolInsertOptions.value.length) %
      filteredSymbolInsertOptions.value.length;
    return;
  }

  if (event.key === 'Enter' || event.key === 'Tab') {
    event.preventDefault();
    const option = filteredSymbolInsertOptions.value[activeAutocompleteIndex.value];
    if (option) {
      void applyAutocompleteOption(option.key);
    }
    return;
  }

  if (event.key === 'Escape') {
    event.preventDefault();
    dismissedTriggerStart.value = activeSymbolTrigger.value?.start ?? null;
  }
};

const applyAutocompleteOption = async (symbolKey: string): Promise<void> => {
  const trigger = activeSymbolTrigger.value;
  if (!trigger) {
    return;
  }

  const { nextText, nextCaretIndex } = applySymbolAutocomplete(
    rulesTextValue.value,
    trigger,
    symbolKey,
  );

  rulesTextValue.value = nextText;
  rulesTextCaretIndex.value = nextCaretIndex;
  dismissedTriggerStart.value = null;
  emit('update-field', 'rules_text', nextText);

  await nextTick();
  rulesTextTextarea.value?.focus();
  rulesTextTextarea.value?.setSelectionRange(nextCaretIndex, nextCaretIndex);
};

const handleReparseTemplateChange = (value: string | number | null): void => {
  if (typeof value === 'string') {
    emit('update-reparse-template', value);
  }
};
</script>
