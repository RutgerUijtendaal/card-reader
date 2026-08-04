<template>
  <AppModal
    :open="open"
    :aria-labelledby="titleId"
    panel-class="theme-popover w-full max-w-md shadow-xl"
    :close-disabled="loading"
    @close="emit('cancel')"
  >
    <h3
      :id="titleId"
      class="theme-section-title text-base font-semibold"
    >
      {{ title }}
    </h3>
    <p class="theme-section-muted mt-2 whitespace-pre-line text-sm">
      {{ message }}
    </p>
    <div class="mt-4 flex justify-end gap-2">
      <button
        class="btn-secondary"
        type="button"
        :disabled="loading"
        @click="emit('cancel')"
      >
        {{ cancelLabel }}
      </button>
      <button
        class="btn-danger-secondary"
        type="button"
        :disabled="loading"
        @click="emit('confirm')"
      >
        {{ loading ? loadingLabel : confirmLabel }}
      </button>
    </div>
  </AppModal>
</template>

<script setup lang="ts">
import { useId } from 'vue';
import AppModal from '@/shared/components/modals/AppModal.vue';

withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    message: string;
    confirmLabel?: string;
    cancelLabel?: string;
    loading?: boolean;
    loadingLabel?: string;
  }>(),
  {
    confirmLabel: 'Confirm',
    cancelLabel: 'Cancel',
    loading: false,
    loadingLabel: 'Working...',
  },
);

const emit = defineEmits<{
  (e: 'confirm'): void;
  (e: 'cancel'): void;
}>();

const titleId = `confirm-modal-title-${useId()}`;
</script>
