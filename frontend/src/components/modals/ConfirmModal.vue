<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="theme-overlay fixed inset-0 z-50 flex items-center justify-center p-4"
      @click.self="emit('cancel')"
    >
      <div class="theme-popover w-full max-w-md shadow-xl">
        <h3 class="theme-section-title text-base font-semibold">
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
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
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
</script>
