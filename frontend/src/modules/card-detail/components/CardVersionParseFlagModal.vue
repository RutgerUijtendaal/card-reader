<template>
  <AppModal
    :open="open"
    aria-labelledby="parse-flag-title"
    overlay-class="bg-black/55"
    panel-class="theme-popover app-scrollbar max-h-[90vh] w-full max-w-5xl overflow-y-auto p-5"
    :close-disabled="submitting"
    @close="requestClose"
  >
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <h2
          id="parse-flag-title"
          class="theme-section-title text-lg font-semibold"
        >
          Flag Parse Issue
        </h2>
        <p class="theme-section-muted mt-1 text-sm">
          Report incorrect parsed properties, suggest an overall card change, or both.
        </p>
      </div>
      <button
        class="btn-secondary h-9"
        type="button"
        :disabled="submitting"
        @click="requestClose"
      >
        Close
      </button>
    </div>

    <div class="mt-5 grid min-h-[22rem] gap-4 md:grid-cols-[16rem_minmax(0,1fr)]">
      <aside class="theme-muted-panel app-scrollbar max-h-[26rem] overflow-y-auto p-2">
        <p class="theme-kicker px-3 pb-2 pt-1 text-[11px] font-semibold uppercase tracking-wide">
          Card suggestion
        </p>
        <button
          class="relative w-full rounded-lg px-3 py-2 text-left transition-colors"
          :class="isFlagged('overall')
            ? 'theme-selected-surface'
            : 'hover:bg-[var(--color-surface-muted)]'"
          type="button"
          :disabled="submitting"
          :aria-pressed="activePropertyKey === 'overall'"
          @click="selectProperty('overall')"
        >
          <span
            v-if="activePropertyKey === 'overall'"
            class="absolute inset-y-2 left-0 w-1 rounded-r-full bg-[var(--color-control-accent)]"
            data-tab-selected-indicator
            aria-hidden="true"
          />
          <span class="theme-section-title flex items-center gap-2 text-sm font-semibold">
            <span class="min-w-0 flex-1">Overall card suggestion</span>
            <span
              v-if="isFlagged('overall')"
              class="theme-pill theme-pill-warning px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
            >
              Active
            </span>
          </span>
          <span class="theme-section-muted mt-1 block text-xs">
            Suggest a change not tied to one parsed property.
          </span>
        </button>

        <p
          class="theme-kicker theme-divider mx-1 mt-3 border-t px-2 pb-2 pt-3 text-[11px] font-semibold uppercase tracking-wide"
        >
          Parsed properties
        </p>
        <button
          v-for="property in propertyOptions"
          :key="property.key"
          class="relative w-full rounded-lg px-3 py-2 text-left transition-colors"
          :class="isFlagged(property.key)
            ? 'theme-selected-surface'
            : 'hover:bg-[var(--color-surface-muted)]'"
          type="button"
          :disabled="submitting"
          :aria-pressed="activePropertyKey === property.key"
          @click="selectProperty(property.key)"
        >
          <span
            v-if="activePropertyKey === property.key"
            class="absolute inset-y-2 left-0 w-1 rounded-r-full bg-[var(--color-control-accent)]"
            data-tab-selected-indicator
            aria-hidden="true"
          />
          <span class="theme-section-title flex items-center gap-2 text-sm font-semibold">
            <span class="min-w-0 flex-1 truncate">{{ property.label }}</span>
            <span
              v-if="isFlagged(property.key)"
              class="theme-pill theme-pill-warning px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
            >
              Active
            </span>
          </span>
          <span
            class="theme-section-muted mt-1 block truncate text-xs"
            :title="property.currentValue || 'Empty'"
          >
            {{ property.currentValue || 'Empty' }}
          </span>
        </button>
      </aside>

      <div class="theme-muted-panel p-4">
        <div
          v-if="activeItem"
          class="flex h-full flex-col"
        >
          <div v-if="activeItem.property_key !== 'overall'">
            <p class="theme-section-title text-base font-semibold">
              {{ parseFlagPropertyLabels[activeItem.property_key] }}
            </p>
            <p
              class="theme-section-muted mt-1 truncate text-xs"
              :title="currentValue(activeItem.property_key) || 'Empty'"
            >
              {{ currentValue(activeItem.property_key) || 'Empty' }}
            </p>
          </div>

          <template v-if="activeItem.property_key === 'overall'">
            <div>
              <p class="theme-section-title text-base font-semibold">
                Overall card suggestion
              </p>
              <p class="theme-section-muted mt-1 text-xs">
                Describe the change you would recommend for this card.
              </p>
            </div>
            <label class="field-label mt-4">
              Suggestion
              <textarea
                ref="requiredInput"
                v-model="activeItem.note"
                class="input-base min-h-40"
                :disabled="submitting"
                placeholder="Required"
              />
            </label>
          </template>

          <template v-else>
            <label class="field-label mt-4">
              What should it be? (required)
              <input
                ref="requiredInput"
                v-model="activeItem.expected_value"
                class="input-base"
                :disabled="submitting"
                placeholder="Required to flag this property"
              >
            </label>
            <label class="field-label mt-4">
              Note
              <textarea
                v-model="activeItem.note"
                class="input-base min-h-32"
                :disabled="submitting"
                placeholder="Optional"
              />
            </label>
          </template>
        </div>

        <div
          v-else
          class="theme-empty-state flex h-full min-h-64 items-center justify-center"
        >
          Select an overall suggestion or parsed property to report.
        </div>
      </div>
    </div>

    <div class="theme-divider mt-5 flex flex-wrap items-center justify-end gap-3 border-t pt-4">
      <p
        v-if="errorMessage"
        class="mr-auto text-sm text-rose-500"
      >
        {{ errorMessage }}
      </p>
      <button
        class="btn-secondary"
        type="button"
        :disabled="submitting"
        @click="requestClose"
      >
        Cancel
      </button>
      <button
        class="btn-primary"
        type="button"
        :disabled="submitting || !canSubmit"
        @click="submit"
      >
        {{ submitting ? 'Submitting...' : 'Submit Flag' }}
      </button>
    </div>
  </AppModal>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import AppModal from '@/components/modals/AppModal.vue';
import type {
  CardVersionDetail,
  ParseFlagCreatePayload,
  ParseFlagItemDraft,
  ParseFlagPropertyKey,
} from '@/modules/card-detail/types';
import { parseFlagPropertyLabels } from '@/modules/card-detail/types';

const props = defineProps<{
  open: boolean;
  version: CardVersionDetail | null;
  submitting?: boolean;
  errorMessage?: string;
}>();

const emit = defineEmits<{
  close: [];
  submit: [payload: ParseFlagCreatePayload];
}>();

const itemDrafts = ref<ParseFlagItemDraft[]>([]);
const activePropertyKey = ref<ParseFlagPropertyKey | null>(null);
const requiredInput = ref<HTMLInputElement | HTMLTextAreaElement | null>(null);

const propertyKeys: ParseFlagPropertyKey[] = [
  'name',
  'type_line',
  'mana_cost',
  'attack',
  'health',
  'rules_text',
  'keywords',
  'tags',
  'types',
  'symbols',
  'other',
];

const propertyOptions = computed(() =>
  propertyKeys.map((key) => ({
    key,
    label: parseFlagPropertyLabels[key],
    currentValue: currentValue(key),
  })),
);

const isFlaggedDraft = (item: ParseFlagItemDraft): boolean =>
  item.property_key === 'overall'
    ? item.note.trim().length > 0
    : item.expected_value.trim().length > 0;

const flaggedItems = computed(() => itemDrafts.value.filter(isFlaggedDraft));
const canSubmit = computed(() => flaggedItems.value.length > 0);

const isFlagged = (propertyKey: ParseFlagPropertyKey): boolean => {
  const item = itemDrafts.value.find((draft) => draft.property_key === propertyKey);
  return item ? isFlaggedDraft(item) : false;
};

const activeItem = computed(
  () => itemDrafts.value.find((item) => item.property_key === activePropertyKey.value) ?? null,
);

const focusRequiredInput = async (): Promise<void> => {
  await nextTick();
  await nextTick();
  requiredInput.value?.focus();
};

const selectProperty = (propertyKey: ParseFlagPropertyKey): void => {
  if (!itemDrafts.value.some((item) => item.property_key === propertyKey)) {
    itemDrafts.value = [
      ...itemDrafts.value,
      { property_key: propertyKey, expected_value: '', note: '' },
    ];
  }
  activePropertyKey.value = propertyKey;
  void focusRequiredInput();
};

const currentValue = (propertyKey: ParseFlagPropertyKey): string => {
  const version = props.version;
  if (!version) return '';
  if (propertyKey === 'keywords') return version.keywords.join(', ');
  if (propertyKey === 'tags') return version.tags.map((row) => row.label).join(', ');
  if (propertyKey === 'types') return version.types.map((row) => row.label).join(', ');
  if (propertyKey === 'symbols') return version.symbols.map((row) => row.label).join(', ');
  if (propertyKey === 'overall' || propertyKey === 'other') return '';
  const value =
    propertyKey === 'rules_text'
      ? version.rules_text_enriched || version.rules_text
      : version[propertyKey];
  return value === null || value === undefined ? '' : String(value);
};

const submit = (): void => {
  emit('submit', {
    note: '',
    items: flaggedItems.value.map((item) => ({ ...item })),
  });
};

const requestClose = (): void => {
  if (!props.submitting) {
    emit('close');
  }
};

watch(
  () => props.open,
  (open) => {
    if (!open) {
      itemDrafts.value = [];
      activePropertyKey.value = null;
      return;
    }
    selectProperty('overall');
  },
  { immediate: true },
);
</script>
