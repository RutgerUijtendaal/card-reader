<template>
  <section class="grid gap-6 xl:h-[calc(100vh-3rem)] xl:grid-cols-[380px_minmax(0,1fr)] xl:items-start">
    <div class="space-y-6 xl:sticky xl:top-0">
      <header class="page-card overflow-hidden">
        <div class="space-y-3">
          <p class="theme-kicker text-xs font-semibold uppercase tracking-[0.22em]">
            Intake Queue
          </p>
          <div class="space-y-2">
            <h2 class="theme-section-title text-2xl font-semibold">
              Import Jobs
            </h2>
            <p class="theme-section-muted max-w-2xl text-sm leading-6">
              Queue new card image batches, monitor parser throughput, and interrupt active jobs
              without killing the parser process.
            </p>
          </div>
          <div class="theme-section-muted flex flex-wrap gap-3 pt-1 text-sm">
            <div class="theme-pill theme-pill-neutral px-3 py-1.5 text-sm">
              {{ queuedCount }} queued
            </div>
            <div class="theme-pill theme-pill-warning px-3 py-1.5 text-sm">
              {{ runningCount + cancelingCount }} active
            </div>
            <div class="theme-pill theme-pill-success px-3 py-1.5 text-sm">
              {{ completedCount }} completed
            </div>
            <div class="theme-pill theme-pill-danger px-3 py-1.5 text-sm">
              {{ failedCount + cancelledCount }} stopped
            </div>
          </div>
        </div>
      </header>

      <form
        class="page-card rounded-[1.75rem] p-6 shadow-sm"
        @submit.prevent="createJobFromPicker"
      >
        <div class="mb-5 flex items-center justify-between gap-3">
          <div class="grid gap-3">
            <div>
              <h3 class="theme-section-title text-base font-semibold">
                New Import
              </h3>
              <p class="theme-section-muted text-sm">
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

          <div class="theme-muted-panel rounded-[1.25rem] px-4 py-4">
            <div class="theme-kicker text-xs font-semibold uppercase tracking-[0.18em]">
              Selection
            </div>
            <div class="theme-section-title mt-2 text-sm">
              {{ pickedFiles.length }} file{{ pickedFiles.length === 1 ? '' : 's' }} ready
            </div>
          </div>

          <p
            v-if="templates.length === 0"
            class="theme-alert-warning"
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
        class="theme-alert-danger"
      >
        {{ errorMessage }}
      </p>
    </div>

    <section class="page-card flex min-h-0 flex-col overflow-hidden xl:h-full">
      <div class="theme-divider flex flex-wrap items-center justify-between gap-3 border-b px-1 pb-4">
        <div class="space-y-1">
          <h3 class="theme-section-title text-base font-semibold">
            Queue Monitor
          </h3>
          <p class="theme-section-muted text-sm">
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
        class="app-scrollbar min-h-0 flex-1 overflow-y-auto pt-5"
      >
        <div
          v-if="jobs.length === 0"
          class="theme-empty-state rounded-[1.5rem] px-6 py-10 text-center"
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
            class="theme-card-frame rounded-[1.75rem] px-6 py-6"
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
                  <span class="theme-kicker text-xs">
                    {{ job.id }}
                  </span>
                </div>
                <div class="space-y-1.5">
                  <p class="theme-section-title text-sm font-semibold">
                    {{ job.template_id }}
                  </p>
                  <p class="theme-section-muted break-all text-sm leading-6">
                    {{ job.source_path }}
                  </p>
                </div>
              </div>

              <div class="flex flex-wrap items-center gap-2 pl-1">
                <button
                  v-if="canCancel(job)"
                  class="btn-danger-secondary rounded-full px-3 py-1.5"
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
                <div class="theme-section-muted flex items-center justify-between text-sm">
                  <span>Progress</span>
                  <span>{{ job.processed_items }}/{{ job.total_items }}</span>
                </div>
                <div class="theme-card-frame-muted h-2.5 rounded-full">
                  <div
                    class="h-full rounded-full transition-all"
                    :class="progressClass(job.status)"
                    :style="{ width: `${progressPercent(job)}%` }"
                  />
                </div>
              </div>

              <dl class="theme-section-muted grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
                <div>
                  <dt class="theme-kicker text-xs uppercase tracking-[0.16em]">
                    Created
                  </dt>
                  <dd class="theme-section-title mt-1.5">
                    {{ formatTimestamp(job.created_at) }}
                  </dd>
                </div>
                <div>
                  <dt class="theme-kicker text-xs uppercase tracking-[0.16em]">
                    Updated
                  </dt>
                  <dd class="theme-section-title mt-1.5">
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
  if (status === 'queued') return 'theme-pill-neutral';
  if (status === 'running') return 'theme-pill-warning';
  if (status === 'canceling') return 'theme-pill-warning';
  if (status === 'cancelled') return 'theme-pill-neutral';
  if (status === 'completed') return 'theme-pill-success';
  return 'theme-pill-danger';
};

const progressClass = (status: ImportJobStatus): string => {
  if (status === 'failed') return 'bg-rose-500';
  if (status === 'cancelled' || status === 'canceling') return 'bg-amber-500';
  if (status === 'completed') return 'bg-emerald-500';
  return 'bg-slate-500';
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
