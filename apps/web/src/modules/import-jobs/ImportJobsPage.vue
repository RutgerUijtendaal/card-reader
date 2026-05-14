<template>
  <section class="grid gap-6 xl:h-[calc(100vh-4rem)] xl:grid-cols-[380px_minmax(0,1fr)] xl:items-start">
    <div class="space-y-6 xl:sticky xl:top-0">
      <header class="page-card overflow-hidden">
        <div class="space-y-3">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-teal-700">
            Intake Queue
          </p>
          <div class="space-y-2">
            <h2 class="text-2xl font-semibold text-slate-900">
              Import Jobs
            </h2>
            <p class="max-w-2xl text-sm leading-6 text-slate-600">
              Queue new card image batches, monitor parser throughput, and interrupt active jobs
              without killing the parser process.
            </p>
          </div>
          <div class="flex flex-wrap gap-3 pt-1 text-sm text-slate-600">
            <div class="rounded-full bg-slate-100 px-3 py-1.5">
              {{ queuedCount }} queued
            </div>
            <div class="rounded-full bg-amber-100 px-3 py-1.5 text-amber-800">
              {{ runningCount + cancelingCount }} active
            </div>
            <div class="rounded-full bg-emerald-100 px-3 py-1.5 text-emerald-800">
              {{ completedCount }} completed
            </div>
            <div class="rounded-full bg-rose-100 px-3 py-1.5 text-rose-800">
              {{ failedCount + cancelledCount }} stopped
            </div>
          </div>
        </div>
      </header>

      <form
        class="page-card rounded-[1.75rem] border border-slate-200 bg-white/90 p-6 shadow-sm"
        @submit.prevent="createJobFromPicker"
      >
        <div class="mb-5 flex items-center justify-between gap-3">
          <div class="grid gap-3">
            <div>
              <h3 class="text-base font-semibold text-slate-900">
                New Import
              </h3>
              <p class="text-sm text-slate-500">
                Upload one file or a whole folder into the parser queue.
              </p>
            </div>
          </div>
        </div>

        <div class="grid gap-4">
          <label class="field-label">
            Template
            <select
              v-model="pickerTemplateId"
              class="input-base"
              required
            >
              <option
                v-for="item in templates"
                :key="item.id"
                :value="item.key"
              >
                {{ item.label }} ({{ item.key }})
              </option>
            </select>
          </label>

          <label class="field-label">
            Pick mode
            <select
              v-model="pickerMode"
              class="input-base"
            >
              <option value="single">Single file</option>
              <option value="directory">Directory</option>
            </select>
          </label>

          <label
            v-if="pickerMode === 'single'"
            class="field-label"
          >
            Select image file
            <input
              class="input-base"
              type="file"
              accept=".png,.jpg,.jpeg,.webp,image/*"
              @change="onSingleFileSelected"
            >
          </label>

          <label
            v-else
            class="field-label"
          >
            Select directory
            <input
              class="input-base"
              type="file"
              multiple
              webkitdirectory
              directory
              @change="onDirectorySelected"
            >
          </label>

          <div class="rounded-[1.25rem] bg-slate-50 px-4 py-4">
            <div class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Selection
            </div>
            <div class="mt-2 text-sm text-slate-700">
              {{ pickedFiles.length }} file{{ pickedFiles.length === 1 ? '' : 's' }} ready
            </div>
          </div>

          <p
            v-if="templates.length === 0"
            class="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
          >
            No templates available. Add one in Settings > Templates first.
          </p>

          <button
            class="btn-primary w-full justify-center"
            type="submit"
            :disabled="pickedFiles.length === 0 || templates.length === 0 || creatingJob"
          >
            {{ creatingJob ? 'Queueing Import...' : 'Queue Import Job' }}
          </button>
        </div>
      </form>

      <p
        v-if="errorMessage"
        class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700"
      >
        {{ errorMessage }}
      </p>
    </div>

    <section class="page-card flex min-h-0 flex-col overflow-hidden xl:h-full">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-1 pb-4">
        <div class="space-y-1">
          <h3 class="text-base font-semibold text-slate-900">
            Queue Monitor
          </h3>
          <p class="text-sm text-slate-500">
            {{ isRefreshing ? 'Refreshing live status...' : 'Live status idle.' }}
            <span v-if="lastRefreshedAt">Last update {{ lastRefreshedAt }}.</span>
          </p>
        </div>
        <button
          class="btn-secondary"
          type="button"
          :disabled="isRefreshing"
          @click="loadJobs"
        >
          {{ isRefreshing ? 'Refreshing...' : 'Refresh Now' }}
        </button>
      </div>

      <div
        class="min-h-0 flex-1 overflow-y-auto pt-5"
      >
        <div
          v-if="jobs.length === 0"
          class="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-sm text-slate-500"
        >
          No import jobs yet.
        </div>

        <div
          v-else
          class="grid gap-5 pr-1"
        >
          <article
            v-for="job in jobs"
            :key="job.id"
            class="rounded-[1.75rem] border border-slate-200 bg-white px-6 py-6 shadow-sm"
          >
            <div class="flex flex-wrap items-start justify-between gap-5">
              <div class="min-w-0 space-y-3 pr-2">
                <div class="flex flex-wrap items-center gap-2">
                  <span
                    class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.16em]"
                    :class="statusClass(job.status)"
                  >
                    {{ job.status }}
                  </span>
                  <span class="text-xs text-slate-400">
                    {{ job.id }}
                  </span>
                </div>
                <div class="space-y-1.5">
                  <p class="text-sm font-semibold text-slate-900">
                    {{ job.template_id }}
                  </p>
                  <p class="break-all text-sm leading-6 text-slate-500">
                    {{ job.source_path }}
                  </p>
                </div>
              </div>

              <div class="flex flex-wrap items-center gap-2 pl-1">
                <button
                  v-if="canCancel(job)"
                  class="rounded-full border border-rose-300 px-3 py-1.5 text-sm font-medium text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
                  type="button"
                  :disabled="cancellingJobIds.has(job.id)"
                  @click="cancelJob(job.id)"
                >
                  {{ cancellingJobIds.has(job.id) ? 'Interrupting...' : 'Interrupt Job' }}
                </button>
              </div>
            </div>

            <div class="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
              <div class="space-y-2.5">
                <div class="flex items-center justify-between text-sm text-slate-600">
                  <span>Progress</span>
                  <span>{{ job.processed_items }}/{{ job.total_items }}</span>
                </div>
                <div class="h-2.5 overflow-hidden rounded-full bg-slate-100">
                  <div
                    class="h-full rounded-full transition-all"
                    :class="progressClass(job.status)"
                    :style="{ width: `${progressPercent(job)}%` }"
                  />
                </div>
              </div>

              <dl class="grid grid-cols-2 gap-x-8 gap-y-3 text-sm text-slate-600">
                <div>
                  <dt class="text-xs uppercase tracking-[0.16em] text-slate-400">
                    Created
                  </dt>
                  <dd class="mt-1.5 text-slate-700">
                    {{ formatTimestamp(job.created_at) }}
                  </dd>
                </div>
                <div>
                  <dt class="text-xs uppercase tracking-[0.16em] text-slate-400">
                    Updated
                  </dt>
                  <dd class="mt-1.5 text-slate-700">
                    {{ formatTimestamp(job.updated_at) }}
                  </dd>
                </div>
              </dl>
            </div>
          </article>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { useDocumentVisibility, useIntervalFn } from '@vueuse/core';
import { computed, onMounted, ref, watch } from 'vue';
import { api } from '@/api/client';
import { fetchTemplates } from '@/modules/settings/api/templates';
import type { TemplateRecord } from '@/modules/settings/types';

type ImportJobStatus = 'queued' | 'running' | 'canceling' | 'cancelled' | 'completed' | 'failed';

type ImportJob = {
  id: string;
  source_path: string;
  template_id: string;
  status: ImportJobStatus;
  total_items: number;
  processed_items: number;
  created_at: string;
  updated_at: string;
};

const pickerTemplateId = ref('mtg-like-v1');
const pickerMode = ref<'single' | 'directory'>('single');
const pickedFiles = ref<File[]>([]);
const errorMessage = ref('');
const jobs = ref<ImportJob[]>([]);
const isRefreshing = ref(false);
const creatingJob = ref(false);
const cancellingJobIds = ref<Set<string>>(new Set());
const lastRefreshedAt = ref<string | null>(null);
const templates = ref<TemplateRecord[]>([]);
const documentVisibility = useDocumentVisibility();

const queuedCount = computed(() => jobs.value.filter((job) => job.status === 'queued').length);
const runningCount = computed(() => jobs.value.filter((job) => job.status === 'running').length);
const cancelingCount = computed(() => jobs.value.filter((job) => job.status === 'canceling').length);
const completedCount = computed(() => jobs.value.filter((job) => job.status === 'completed').length);
const failedCount = computed(() => jobs.value.filter((job) => job.status === 'failed').length);
const cancelledCount = computed(() => jobs.value.filter((job) => job.status === 'cancelled').length);

const loadJobs = async (): Promise<void> => {
  isRefreshing.value = true;
  try {
    const response = await api.get<ImportJob[]>('/imports');
    jobs.value = response.data;
    lastRefreshedAt.value = new Date().toLocaleTimeString();
  } finally {
    isRefreshing.value = false;
  }
};

const createJobFromPicker = async (): Promise<void> => {
  errorMessage.value = '';
  if (pickedFiles.value.length === 0) {
    errorMessage.value = 'Please select at least one file.';
    return;
  }

  creatingJob.value = true;
  const formData = new FormData();
  formData.append('template_id', pickerTemplateId.value);
  formData.append('options_json', JSON.stringify({}));
  pickedFiles.value.forEach((file) => formData.append('files', file));

  try {
    await api.post('/imports/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    pickedFiles.value = [];
  } catch (error) {
    console.error('Create import from upload failed', error);
    errorMessage.value = extractError(error);
    return;
  } finally {
    creatingJob.value = false;
  }

  try {
    await loadJobs();
  } catch (error) {
    console.error('Refresh imports after upload create failed', error);
    errorMessage.value = 'Import was created, but refreshing the jobs list failed.';
  }
};

const cancelJob = async (jobId: string): Promise<void> => {
  const next = new Set(cancellingJobIds.value);
  if (next.has(jobId)) return;
  next.add(jobId);
  cancellingJobIds.value = next;
  errorMessage.value = '';

  try {
    await api.post(`/imports/${jobId}/cancel`);
    await loadJobs();
  } catch (error) {
    console.error('Cancel import job failed', error);
    errorMessage.value = extractError(error);
  } finally {
    const done = new Set(cancellingJobIds.value);
    done.delete(jobId);
    cancellingJobIds.value = done;
  }
};

const loadTemplates = async (): Promise<void> => {
  templates.value = await fetchTemplates();
  if (templates.value.length === 0) {
    pickerTemplateId.value = '';
    return;
  }
  const stillExists = templates.value.some((item) => item.key === pickerTemplateId.value);
  if (!stillExists) {
    pickerTemplateId.value = templates.value[0].key;
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

const canCancel = (job: ImportJob): boolean => job.status === 'queued' || job.status === 'running';

const hasActiveJobs = computed<boolean>(() =>
  jobs.value.some((job) => job.status === 'queued' || job.status === 'running' || job.status === 'canceling'));

const progressPercent = (job: ImportJob): number => {
  if (job.total_items <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((job.processed_items / job.total_items) * 100)));
};

const statusClass = (status: ImportJobStatus): string => {
  if (status === 'queued') return 'bg-slate-100 text-slate-700';
  if (status === 'running') return 'bg-amber-100 text-amber-800';
  if (status === 'canceling') return 'bg-orange-100 text-orange-800';
  if (status === 'cancelled') return 'bg-slate-200 text-slate-700';
  if (status === 'completed') return 'bg-emerald-100 text-emerald-800';
  return 'bg-rose-100 text-rose-800';
};

const progressClass = (status: ImportJobStatus): string => {
  if (status === 'failed') return 'bg-rose-500';
  if (status === 'cancelled' || status === 'canceling') return 'bg-orange-400';
  if (status === 'completed') return 'bg-emerald-500';
  return 'bg-teal-500';
};

const formatTimestamp = (value: string): string => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

const extractError = (error: unknown): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const maybeResponse = (error as { response?: { data?: { detail?: unknown }; status?: number } })
      .response;
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

const pollJobs = async (): Promise<void> => {
  if (documentVisibility.value !== 'visible') return;
  if (!hasActiveJobs.value) return;
  try {
    await loadJobs();
  } catch (error) {
    console.error('Polling imports failed', error);
  }
};

const { pause: pausePolling, resume: resumePolling } = useIntervalFn(() => {
  void pollJobs();
}, 2000, { immediate: false });

watch(
  [documentVisibility, hasActiveJobs],
  ([visibility, hasActive]) => {
    if (visibility === 'visible' && hasActive) {
      resumePolling();
      void pollJobs();
      return;
    }

    pausePolling();
  },
  { immediate: true },
);

onMounted(async () => {
  await loadTemplates();
  await loadJobs();
});
</script>
