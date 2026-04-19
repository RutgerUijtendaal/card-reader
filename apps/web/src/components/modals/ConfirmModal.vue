<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      @click.self="emit('cancel')"
    >
      <div class="w-full max-w-md rounded-lg border border-slate-200 bg-white p-4 shadow-xl">
        <h3 class="text-base font-semibold text-slate-900">{{ title }}</h3>
        <p class="mt-2 whitespace-pre-line text-sm text-slate-600">{{ message }}</p>
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
            class="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
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
    loadingLabel: 'Working...'
  }
);

const emit = defineEmits<{
  (e: 'confirm'): void;
  (e: 'cancel'): void;
}>();
</script>
