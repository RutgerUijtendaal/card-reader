<template>
  <div class="space-y-4">
    <div
      class="theme-card-frame-muted flex min-h-52 flex-col items-center justify-center rounded-xl border-dashed px-5 py-8 text-center transition"
      :class="isDragging ? 'theme-selected-surface' : ''"
      @dragenter.prevent="isDragging = true"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
    >
      <span class="theme-muted-panel inline-flex h-12 w-12 items-center justify-center rounded-full">
        <UploadCloud class="h-6 w-6" />
      </span>
      <h4 class="theme-section-title mt-4 text-base font-semibold">
        Drop card images here
      </h4>
      <p class="theme-section-muted mt-1 max-w-md text-sm leading-6">
        Drop one or more PNG, JPG, JPEG, or WebP images, or browse for an image or folder.
      </p>

      <div class="mt-5 flex w-full flex-col justify-center gap-3 sm:w-auto sm:flex-row">
        <button
          class="btn-secondary inline-flex justify-center gap-2"
          type="button"
          @click="singleInput?.click()"
        >
          <ImagePlus class="h-4 w-4" />
          Choose image
        </button>
        <button
          class="btn-secondary inline-flex justify-center gap-2"
          type="button"
          @click="directoryInput?.click()"
        >
          <FolderOpen class="h-4 w-4" />
          Choose folder
        </button>
      </div>

      <input
        :key="`single-${resetKey}`"
        ref="singleInput"
        class="hidden"
        type="file"
        accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
        @change="onSingleFileSelected"
      >
      <input
        :key="`directory-${resetKey}`"
        ref="directoryInput"
        class="hidden"
        type="file"
        accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
        multiple
        webkitdirectory
        directory
        @change="onDirectorySelected"
      >
    </div>

    <p
      v-if="selectionError"
      class="theme-alert-danger text-sm"
      role="alert"
    >
      {{ selectionError }}
    </p>

    <section
      v-if="files.length > 0"
      class="theme-muted-panel space-y-3 px-4 py-4"
      aria-labelledby="import-selection-heading"
    >
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4
            id="import-selection-heading"
            class="theme-section-title text-sm font-semibold"
          >
            {{ sourceLabel }}
          </h4>
          <p class="theme-section-muted mt-1 text-xs">
            {{ files.length }} image{{ files.length === 1 ? '' : 's' }} · {{ formattedTotalSize }}
          </p>
        </div>
        <button
          class="theme-link rounded px-1 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-input-focus)]"
          type="button"
          @click="clearSelection"
        >
          Clear
        </button>
      </div>

      <ul class="text-sm">
        <li
          v-for="file in visibleFiles"
          :key="`${file.name}-${file.size}-${file.lastModified}`"
          class="theme-divider flex min-w-0 items-center justify-between gap-3 border-b py-2 first:pt-0 last:border-b-0 last:pb-0"
        >
          <span
            class="theme-section-title min-w-0 truncate"
            :title="file.name"
          >
            {{ file.name }}
          </span>
          <span class="theme-section-muted shrink-0 text-xs">
            {{ formatFileSize(file.size) }}
          </span>
        </li>
      </ul>
      <p
        v-if="additionalFileCount > 0"
        class="theme-section-muted text-xs"
      >
        +{{ additionalFileCount }} more image{{ additionalFileCount === 1 ? '' : 's' }}
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { FolderOpen, ImagePlus, UploadCloud } from 'lucide-vue-next';
import { computed, ref, watch } from 'vue';

const SUPPORTED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp'];
const VISIBLE_FILE_LIMIT = 5;

const props = defineProps<{
  files: File[];
  resetKey: number;
}>();

const emit = defineEmits<{
  select: [files: File[]];
  clear: [];
}>();

const singleInput = ref<HTMLInputElement | null>(null);
const directoryInput = ref<HTMLInputElement | null>(null);
const isDragging = ref(false);
const selectionError = ref('');
const sourceKind = ref<'image' | 'folder' | 'drop' | null>(null);

const visibleFiles = computed(() => props.files.slice(0, VISIBLE_FILE_LIMIT));
const additionalFileCount = computed(() => Math.max(0, props.files.length - VISIBLE_FILE_LIMIT));
const totalSize = computed(() => props.files.reduce((sum, file) => sum + file.size, 0));
const formattedTotalSize = computed(() => formatFileSize(totalSize.value));
const sourceLabel = computed(() => {
  if (sourceKind.value === 'folder') return 'Selected folder';
  if (sourceKind.value === 'drop') return 'Dropped images';
  if (sourceKind.value === 'image') return 'Selected image';
  return 'Selected images';
});

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  const kilobytes = bytes / 1024;
  if (kilobytes < 1024) return `${kilobytes.toFixed(kilobytes >= 10 ? 0 : 1)} KB`;
  const megabytes = kilobytes / 1024;
  return `${megabytes.toFixed(megabytes >= 10 ? 0 : 1)} MB`;
};

const isSupportedImage = (file: File): boolean => {
  if (file.type === 'image/png' || file.type === 'image/jpeg' || file.type === 'image/webp') {
    return true;
  }
  const normalizedName = file.name.toLowerCase();
  return SUPPORTED_IMAGE_EXTENSIONS.some((extension) => normalizedName.endsWith(extension));
};

const selectFiles = (files: File[], kind: 'image' | 'folder' | 'drop'): void => {
  const supportedFiles = files.filter(isSupportedImage);
  const rejectedCount = files.length - supportedFiles.length;

  if (supportedFiles.length === 0) {
    selectionError.value = 'Choose PNG, JPG, JPEG, or WebP card images.';
    return;
  }

  selectionError.value = rejectedCount > 0
    ? `${rejectedCount} unsupported file${rejectedCount === 1 ? ' was' : 's were'} ignored.`
    : '';
  sourceKind.value = kind;
  emit('select', supportedFiles);
};

const onSingleFileSelected = (event: Event): void => {
  const input = event.target as HTMLInputElement;
  selectFiles(input.files ? Array.from(input.files).slice(0, 1) : [], 'image');
};

const onDirectorySelected = (event: Event): void => {
  const input = event.target as HTMLInputElement;
  selectFiles(input.files ? Array.from(input.files) : [], 'folder');
};

const onDrop = (event: DragEvent): void => {
  isDragging.value = false;
  selectFiles(event.dataTransfer?.files ? Array.from(event.dataTransfer.files) : [], 'drop');
};

const clearSelection = (): void => {
  selectionError.value = '';
  sourceKind.value = null;
  emit('clear');
};

watch(
  () => props.resetKey,
  () => {
    isDragging.value = false;
    selectionError.value = '';
    sourceKind.value = null;
  },
);
</script>
