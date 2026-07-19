<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="theme-overlay fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="deck-tag-management-title"
      @click.self="requestClose"
    >
      <div
        ref="dialogRef"
        class="theme-popover app-scrollbar max-h-[90vh] w-full max-w-lg overflow-y-auto p-5 shadow-xl"
        tabindex="-1"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <h2
              id="deck-tag-management-title"
              class="theme-section-title text-lg font-semibold"
            >
              Manage Tags
            </h2>
            <p class="theme-section-muted mt-1 truncate text-sm">
              {{ deckName }}
            </p>
          </div>
          <button
            class="theme-icon-button shrink-0"
            type="button"
            aria-label="Close tag manager"
            title="Close"
            :disabled="saving"
            @click="requestClose"
          >
            <X class="h-4 w-4" />
          </button>
        </div>

        <div class="theme-divider mt-5 min-h-32 border-t pt-5">
          <div
            v-if="loading"
            class="space-y-3"
            aria-label="Loading deck tags"
          >
            <div class="theme-card-frame-muted h-9 animate-pulse rounded-lg" />
            <div class="flex gap-2">
              <div class="theme-card-frame-muted h-7 w-20 animate-pulse rounded-full" />
              <div class="theme-card-frame-muted h-7 w-24 animate-pulse rounded-full" />
            </div>
          </div>

          <div
            v-else-if="errorMessage"
            class="theme-muted-panel flex min-h-28 flex-col items-center justify-center gap-3 p-4 text-center"
          >
            <p class="theme-error-text text-sm">
              {{ errorMessage }}
            </p>
            <button
              class="btn-secondary"
              type="button"
              @click="emit('retry')"
            >
              Retry
            </button>
          </div>

          <DeckTagPicker
            v-else
            :catalog="catalog"
            :model-value="modelValue"
            :suggested-type-labels="suggestedTypeLabels"
            @update:model-value="emit('update:modelValue', $event)"
            @update:suggested-type-labels="emit('update:suggestedTypeLabels', $event)"
          />
        </div>

        <div class="theme-divider mt-5 flex justify-end gap-2 border-t pt-4">
          <button
            class="btn-secondary"
            type="button"
            :disabled="saving"
            @click="requestClose"
          >
            Cancel
          </button>
          <button
            class="btn-primary"
            type="button"
            :disabled="loading || saving || Boolean(errorMessage)"
            @click="emit('save')"
          >
            {{ saving ? 'Saving...' : 'Save Tags' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { onKeyStroke, useFocus, useScrollLock } from '@vueuse/core';
import { X } from 'lucide-vue-next';
import { nextTick, ref, watch } from 'vue';
import DeckTagPicker from '@/components/decks/DeckTagPicker.vue';
import type { DeckTagCatalog } from '@/modules/decks/types';

const props = defineProps<{
  open: boolean;
  deckName: string;
  catalog: DeckTagCatalog;
  modelValue: string[];
  suggestedTypeLabels: string[];
  loading: boolean;
  saving: boolean;
  errorMessage?: string | null;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void;
  (e: 'update:suggestedTypeLabels', value: string[]): void;
  (e: 'save'): void;
  (e: 'cancel'): void;
  (e: 'retry'): void;
}>();

const dialogRef = ref<HTMLElement | null>(null);
const isBodyLocked = useScrollLock(typeof document === 'undefined' ? null : document.body);
const { focused } = useFocus(dialogRef);

const requestClose = (): void => {
  if (!props.saving) {
    emit('cancel');
  }
};

onKeyStroke('Escape', (event) => {
  if (!props.open || props.saving) {
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
      return;
    }
    await nextTick();
    focused.value = true;
  },
  { immediate: true },
);
</script>
