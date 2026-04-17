<template>
  <section class="page-card space-y-5">
    <h2 class="text-xl font-semibold text-slate-900">Import Jobs</h2>

    <div class="grid gap-5">
      <div class="grid gap-3">
        <h3 class="text-base font-semibold text-slate-800">Import with file picker</h3>
        <form class="grid gap-3" @submit.prevent="createJobFromPicker">
          <label class="field-label">
            Template
            <input v-model="pickerTemplateId" class="input-base" required placeholder="mtg-like-v1" />
          </label>

          <label class="field-label">
            Pick mode
            <select v-model="pickerMode" class="input-base">
              <option value="single">Single file</option>
              <option value="directory">Directory</option>
            </select>
          </label>

          <label v-if="pickerMode === 'single'" class="field-label">
            Select image file
            <input class="input-base" type="file" accept=".png,.jpg,.jpeg,.webp,image/*" @change="onSingleFileSelected" />
          </label>

          <label v-else class="field-label">
            Select directory
            <input class="input-base" type="file" multiple webkitdirectory directory @change="onDirectorySelected" />
          </label>

          <p class="text-sm text-slate-600">Selected files: {{ pickedFiles.length }}</p>

          <button class="btn-primary w-fit" type="submit" :disabled="pickedFiles.length === 0">
            Create import from picker
          </button>
        </form>
      </div>

      <p v-if="errorMessage" class="text-sm font-medium text-red-700">{{ errorMessage }}</p>
    </div>

    <ul class="grid gap-2">
      <li
        v-for="job in jobs"
        :key="job.id"
        class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700"
      >
        {{ job.id }} - {{ job.status }} ({{ job.processed_items }}/{{ job.total_items }})
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { api } from '@/api/client';

type ImportJob = {
  id: string;
  status: string;
  total_items: number;
  processed_items: number;
};

const pickerTemplateId = ref('mtg-like-v1');
const pickerMode = ref<'single' | 'directory'>('single');
const pickedFiles = ref<File[]>([]);
const errorMessage = ref('');
const jobs = ref<ImportJob[]>([]);

const loadJobs = async (): Promise<void> => {
  const response = await api.get<ImportJob[]>('/imports');
  jobs.value = response.data;
};

const createJobFromPicker = async (): Promise<void> => {
  errorMessage.value = '';
  if (pickedFiles.value.length === 0) {
    errorMessage.value = 'Please select at least one file.';
    return;
  }

  const formData = new FormData();
  formData.append('template_id', pickerTemplateId.value);
  formData.append('options_json', JSON.stringify({}));
  pickedFiles.value.forEach((file) => formData.append('files', file));

  try {
    await api.post('/imports/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  } catch (error) {
    console.error('Create import from upload failed', error);
    errorMessage.value = extractError(error);
    return;
  }

  try {
    await loadJobs();
  } catch (error) {
    console.error('Refresh imports after upload create failed', error);
    errorMessage.value = 'Import was created, but refreshing the jobs list failed.';
  }
};

const onSingleFileSelected = (event: Event): void => {
  const input = event.target as HTMLInputElement;
  pickedFiles.value = input.files ? Array.from(input.files).slice(0, 1) : [];
};

const onDirectorySelected = (event: Event): void => {
  const input = event.target as HTMLInputElement;
  pickedFiles.value = input.files ? Array.from(input.files) : [];
};

const extractError = (error: unknown): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const maybeResponse = (error as { response?: { data?: { detail?: unknown }; status?: number } }).response;
    const detail = maybeResponse?.data?.detail;
    if (typeof detail === 'string' && detail.length > 0) {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((entry) => {
          if (typeof entry === 'string') return entry;
          if (entry && typeof entry === 'object' && 'msg' in entry) {
            return String((entry as { msg: unknown }).msg);
          }
          return JSON.stringify(entry);
        })
        .join('; ');
    }
    if (detail && typeof detail === 'object') {
      return JSON.stringify(detail);
    }
    if (maybeResponse?.status) {
      return `Request failed (HTTP ${maybeResponse.status}).`;
    }
  }
  if (typeof error === 'object' && error && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return 'Import request failed.';
};

onMounted(loadJobs);
</script>
