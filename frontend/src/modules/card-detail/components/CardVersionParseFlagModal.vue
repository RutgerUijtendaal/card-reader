<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4"
    role="dialog"
    aria-modal="true"
    aria-labelledby="parse-flag-title"
  >
    <div
      ref="dialogRef"
      class="theme-popover app-scrollbar max-h-[90vh] w-full max-w-5xl overflow-y-auto p-5"
      tabindex="-1"
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
            Select the parsed properties that look wrong.
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
          <button
            v-for="property in propertyOptions"
            :key="property.key"
            class="w-full rounded-lg px-3 py-2 text-left transition-colors"
            :class="activePropertyKey === property.key ? 'theme-selected-surface' : 'hover:bg-[var(--color-surface-muted)]'"
            type="button"
            :disabled="submitting"
            @click="selectProperty(property.key)"
          >
            <span class="theme-section-title flex items-center gap-2 text-sm font-semibold">
              <input
                class="theme-checkbox h-4 w-4"
                type="checkbox"
                :checked="isSelected(property.key)"
                :disabled="submitting"
                tabindex="-1"
                @click.stop="toggleProperty(property.key)"
              >
              <span class="min-w-0 flex-1 truncate">{{ property.label }}</span>
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
            <div>
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

            <label class="field-label mt-4">
              What should it be?
              <input
                v-model="activeItem.expected_value"
                class="input-base"
                :disabled="submitting"
                placeholder="Optional"
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
          </div>

          <div
            v-else
            class="theme-empty-state flex h-full min-h-64 items-center justify-center"
          >
            Select a property to report.
          </div>
        </div>
      </div>

      <label class="field-label mt-5">
        Overall note
        <textarea
          v-model="overallNote"
          class="input-base min-h-24"
          :disabled="submitting"
          placeholder="Optional"
        />
      </label>

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
          :disabled="submitting || selectedItems.length === 0"
          @click="submit"
        >
          {{ submitting ? 'Submitting...' : 'Submit Flag' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onClickOutside, onKeyStroke, useFocus, useScrollLock } from '@vueuse/core';
import { computed, nextTick, ref, watch } from 'vue';
import type {
  CardVersionDetail,
  ParseFlagCreatePayload,
  ParseFlagItemDraft,
  ParseFlagPropertyKey,
} from '@/modules/card-detail/types';
import {
  parseFlagPropertyLabels,
} from '@/modules/card-detail/types';

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

const selectedItems = ref<ParseFlagItemDraft[]>([]);
const activePropertyKey = ref<ParseFlagPropertyKey | null>(null);
const overallNote = ref('');
const dialogRef = ref<HTMLElement | null>(null);
const isBodyLocked = useScrollLock(typeof document === 'undefined' ? null : document.body);
const { focused } = useFocus(dialogRef);

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

const isSelected = (propertyKey: ParseFlagPropertyKey): boolean =>
  selectedItems.value.some((item) => item.property_key === propertyKey);

const activeItem = computed(() =>
  selectedItems.value.find((item) => item.property_key === activePropertyKey.value) ?? null,
);

const selectProperty = (propertyKey: ParseFlagPropertyKey): void => {
  if (!isSelected(propertyKey)) {
    selectedItems.value = [
      ...selectedItems.value,
      { property_key: propertyKey, expected_value: '', note: '' },
    ];
  }
  activePropertyKey.value = propertyKey;
};

const toggleProperty = (propertyKey: ParseFlagPropertyKey): void => {
  if (isSelected(propertyKey)) {
    selectedItems.value = selectedItems.value.filter((item) => item.property_key !== propertyKey);
    if (activePropertyKey.value === propertyKey) {
      activePropertyKey.value = selectedItems.value[0]?.property_key ?? null;
    }
    return;
  }
  selectedItems.value = [
    ...selectedItems.value,
    { property_key: propertyKey, expected_value: '', note: '' },
  ];
  activePropertyKey.value = propertyKey;
};

const currentValue = (propertyKey: ParseFlagPropertyKey): string => {
  const version = props.version;
  if (!version) return '';
  if (propertyKey === 'keywords') return version.keywords.join(', ');
  if (propertyKey === 'tags') return version.tags.map((row) => row.label).join(', ');
  if (propertyKey === 'types') return version.types.map((row) => row.label).join(', ');
  if (propertyKey === 'symbols') return version.symbols.map((row) => row.label).join(', ');
  if (propertyKey === 'other') return '';
  const value = propertyKey === 'rules_text'
    ? version.rules_text_enriched || version.rules_text
    : version[propertyKey];
  return value === null || value === undefined ? '' : String(value);
};

const submit = (): void => {
  emit('submit', {
    note: overallNote.value,
    items: selectedItems.value.map((item) => ({ ...item })),
  });
};

const requestClose = (): void => {
  if (!props.submitting) {
    emit('close');
  }
};

onClickOutside(dialogRef, () => {
  if (props.open) {
    requestClose();
  }
});

onKeyStroke('Escape', (event) => {
  if (!props.open || props.submitting) {
    return;
  }
  event.preventDefault();
  requestClose();
});

watch(
  () => props.open,
  async (open) => {
    isBodyLocked.value = open;
    if (!open) {
      selectedItems.value = [];
      activePropertyKey.value = null;
      overallNote.value = '';
      return;
    }
    await nextTick();
    focused.value = true;
  },
  { immediate: true },
);
</script>
