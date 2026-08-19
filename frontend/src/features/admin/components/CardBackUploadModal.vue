<template>
  <AppModal
    :open="open"
    :aria-labelledby="titleId"
    :aria-describedby="descriptionId"
    :close-disabled="uploading"
    panel-class="theme-popover w-full max-w-2xl shadow-xl"
    @close="requestClose"
  >
    <form @submit.prevent="submitUpload">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h3
            :id="titleId"
            class="theme-section-title text-lg font-semibold"
          >
            Add card back
          </h3>
          <p
            :id="descriptionId"
            class="theme-section-muted mt-1 text-sm"
          >
            Add an image to the reusable library. Pool defaults stay unchanged.
          </p>
        </div>
        <button
          class="btn-secondary inline-flex h-9 w-9 shrink-0 items-center justify-center p-0"
          type="button"
          aria-label="Close add card back dialog"
          :disabled="uploading"
          @click="requestClose"
        >
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="mt-5 grid gap-5 sm:grid-cols-[minmax(0,1fr)_10rem]">
        <div class="space-y-4">
          <label class="field-label">
            Label
            <input
              v-model="label"
              class="input-base"
              placeholder="Card back name"
              autocomplete="off"
            >
          </label>

          <div>
            <span class="field-label">Image</span>
            <button
              class="theme-card-frame-muted mt-1 flex w-full items-center gap-3 rounded-xl border-dashed p-4 text-left transition hover:border-[var(--color-input-focus)]"
              type="button"
              :disabled="uploading"
              @click="fileInput?.click()"
            >
              <span class="theme-muted-panel inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full p-0">
                <ImagePlus class="h-5 w-5" />
              </span>
              <span class="min-w-0">
                <span class="theme-section-title block truncate text-sm font-medium">
                  {{ selectedFile?.name ?? 'Choose an image' }}
                </span>
                <span class="theme-section-muted mt-0.5 block text-xs">
                  PNG, JPG, WebP, BMP, or TIFF
                </span>
              </span>
            </button>
            <input
              ref="fileInput"
              class="hidden"
              type="file"
              accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff"
              @change="selectFile"
            >
          </div>

          <p
            v-if="errorMessage"
            class="theme-alert-danger text-sm"
            role="alert"
          >
            {{ errorMessage }}
          </p>
        </div>

        <div>
          <span class="field-label">Preview</span>
          <div class="theme-card-frame theme-card-image-well mt-1 aspect-[63/88] overflow-hidden rounded-xl">
            <img
              v-if="previewUrl"
              class="h-full w-full object-cover"
              :src="previewUrl"
              alt="Selected card back preview"
            >
            <div
              v-else
              class="theme-section-muted flex h-full flex-col items-center justify-center gap-2 p-4 text-center text-xs"
            >
              <ImagePlus class="h-6 w-6" />
              Choose an image to preview it.
            </div>
          </div>
        </div>
      </div>

      <div class="theme-divider mt-6 flex justify-end gap-3 border-t pt-4">
        <button
          class="btn-secondary"
          type="button"
          :disabled="uploading"
          @click="requestClose"
        >
          Cancel
        </button>
        <button
          class="btn-primary inline-flex items-center justify-center gap-2"
          type="submit"
          :disabled="!selectedFile || uploading"
        >
          <Upload class="h-4 w-4" />
          {{ uploading ? 'Uploading...' : 'Add to library' }}
        </button>
      </div>
    </form>
  </AppModal>
</template>

<script setup lang="ts">
import { ref, shallowRef, useId, watch } from 'vue';
import { useObjectUrl } from '@vueuse/core';
import { ImagePlus, Upload, X } from 'lucide-vue-next';
import AppModal from '@/shared/components/modals/AppModal.vue';

const props = withDefaults(defineProps<{
  open: boolean;
  uploading?: boolean;
  errorMessage?: string;
}>(), {
  uploading: false,
  errorMessage: '',
});

const emit = defineEmits<{
  close: [];
  submit: [payload: { file: File; label: string }];
}>();

const titleId = `card-back-upload-title-${useId()}`;
const descriptionId = `card-back-upload-description-${useId()}`;
const label = ref('');
const selectedFile = shallowRef<File | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const previewUrl = useObjectUrl(selectedFile);

const resetForm = (): void => {
  label.value = '';
  selectedFile.value = null;
  if (fileInput.value) {
    fileInput.value.value = '';
  }
};

const requestClose = (): void => {
  if (!props.uploading) {
    emit('close');
  }
};

const selectFile = (event: Event): void => {
  selectedFile.value = (event.target as HTMLInputElement | null)?.files?.[0] ?? null;
};

const submitUpload = (): void => {
  if (!selectedFile.value || props.uploading) {
    return;
  }
  emit('submit', { file: selectedFile.value, label: label.value });
};

watch(
  () => props.open,
  (open) => {
    if (!open) {
      resetForm();
    }
  },
);
</script>
