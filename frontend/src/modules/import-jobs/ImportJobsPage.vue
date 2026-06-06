<template>
  <section class="flex h-[calc(100vh-3rem)] min-h-0 flex-col gap-6 overflow-hidden">
    <AppPageHeader
      :icon="Upload"
      title="Import Jobs"
      subtitle="Queue card image batches, monitor parser throughput, and interrupt active jobs."
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <button
          class="btn-secondary inline-flex items-center gap-2"
          type="button"
          :disabled="isRefreshing"
          @click="loadJobs"
        >
          <RefreshCw
            class="h-4 w-4"
            :class="isRefreshing ? 'animate-spin' : ''"
          />
          <span>{{ isRefreshing ? 'Refreshing...' : 'Refresh' }}</span>
        </button>
      </template>

      <template #bottomLeft>
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">
            Queue Monitor
          </span>
          <span class="theme-section-muted">
            {{ isRefreshing ? 'Refreshing live status...' : 'Live status idle.' }}
          </span>
          <span
            v-if="lastRefreshedAt"
            class="theme-section-muted"
          >
            Last update {{ lastRefreshedAt }}.
          </span>
        </div>
      </template>

      <template #bottomRight>
        <div class="flex flex-wrap items-center gap-2">
          <div class="theme-pill theme-pill-neutral inline-flex items-center gap-2 px-3 py-1.5 text-sm">
            <span class="text-xs font-semibold uppercase tracking-wide">Queued</span>
            <span class="font-semibold">{{ queuedCount }}</span>
          </div>
          <div class="theme-pill theme-pill-warning inline-flex items-center gap-2 px-3 py-1.5 text-sm">
            <span class="text-xs font-semibold uppercase tracking-wide">Active</span>
            <span class="font-semibold">{{ runningCount + cancelingCount }}</span>
          </div>
          <div class="theme-pill theme-pill-success inline-flex items-center gap-2 px-3 py-1.5 text-sm">
            <span class="text-xs font-semibold uppercase tracking-wide">Completed</span>
            <span class="font-semibold">{{ completedCount }}</span>
          </div>
          <div class="theme-pill theme-pill-danger inline-flex items-center gap-2 px-3 py-1.5 text-sm">
            <span class="text-xs font-semibold uppercase tracking-wide">Stopped</span>
            <span class="font-semibold">{{ failedCount + cancelledCount }}</span>
          </div>
        </div>
      </template>
    </AppPageHeader>

    <section class="grid min-h-0 flex-1 gap-6 overflow-hidden xl:grid-cols-[23rem_minmax(0,1fr)]">
      <form
        id="import-job-form"
        class="theme-divider flex min-h-0 flex-col border-b pb-4 xl:border-b-0 xl:border-r xl:pb-0 xl:pr-3"
        @submit.prevent="createJobFromPicker"
      >
        <div class="app-scrollbar flex-1 space-y-5 overflow-y-auto pr-2">
          <div class="space-y-2">
            <h3 class="theme-section-title text-lg font-semibold">
              New Import
            </h3>
            <p class="theme-section-muted text-sm">
              Upload one file or a whole folder into the parser queue.
            </p>
          </div>

          <div class="theme-muted-panel rounded-xl px-4 py-4">
            <div class="theme-kicker text-xs font-semibold uppercase tracking-[0.18em]">
              Current Version
            </div>
            <div class="theme-section-title mt-2 text-sm">
              {{ currentContentVersion?.version_number ?? 'No version yet' }}
            </div>
            <p
              v-if="currentContentVersion"
              class="theme-section-muted mt-1 text-sm leading-5"
            >
              {{ currentContentVersion.description }}
            </p>
          </div>

          <div class="space-y-4">
            <h4 class="theme-kicker text-xs font-semibold uppercase tracking-[0.18em]">
              Import Metadata
            </h4>

            <label class="field-label">
              Template
              <AppSelect
                v-model="pickerTemplateId"
                :options="templateOptions"
                required
              />
            </label>

            <label class="field-label">
              Version
              <input
                v-model="contentVersionBase"
                class="input-base"
                type="text"
                inputmode="numeric"
                pattern="[0-9]+\.[0-9]+"
                placeholder="14.1"
                title="Use major.minor format, for example 14.1."
                autocomplete="off"
                :aria-invalid="contentVersionBaseError.length > 0"
                aria-describedby="content-version-base-help"
                required
              >
              <span
                id="content-version-base-help"
                class="theme-section-muted text-xs"
                :class="contentVersionBaseError.length > 0 ? 'text-rose-400' : ''"
              >
                {{ contentVersionBaseError || 'Use major.minor format, for example 14.1.' }}
              </span>
            </label>

            <label class="field-label">
              Description
              <textarea
                v-model="contentVersionDescription"
                class="input-base min-h-28 resize-y"
                required
              />
            </label>
          </div>

          <div class="theme-divider space-y-4 border-t pt-5">
            <h4 class="theme-kicker text-xs font-semibold uppercase tracking-[0.18em]">
              Source
            </h4>

            <label class="field-label">
              Pick mode
              <AppSelect
                v-model="pickerMode"
                :options="pickerModeOptions"
              />
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

            <div class="theme-card-frame-muted flex items-center justify-between gap-3 rounded-xl px-4 py-3">
              <span class="theme-kicker text-xs font-semibold uppercase tracking-[0.16em]">
                Selection
              </span>
              <span class="theme-section-title text-sm font-semibold">
                {{ pickedFiles.length }} file{{ pickedFiles.length === 1 ? '' : 's' }}
              </span>
            </div>

            <p
              v-if="templates.length === 0"
              class="theme-alert-warning"
            >
              No templates available. Add one in Admin > Templates first.
            </p>
          </div>
        </div>

        <div class="theme-divider mt-4 space-y-3">
          <p
            v-if="errorMessage"
            class="theme-alert-danger"
          >
            {{ errorMessage }}
          </p>

          <button
            class="btn-primary w-full justify-center"
            type="submit"
            :disabled="pickedFiles.length === 0 || templates.length === 0 || !hasValidVersionInput || creatingJob"
          >
            {{ submitButtonLabel }}
          </button>
        </div>
      </form>

      <section class="flex min-h-0 flex-col overflow-hidden">
        <div class="theme-divider flex flex-wrap items-center justify-between gap-3 border-b px-1 pb-4">
          <div class="space-y-1">
            <h3 class="theme-section-title text-base font-semibold">
              Queue Monitor
            </h3>
            <p class="theme-section-muted text-sm">
              Parser jobs ordered by the latest queue activity.
            </p>
          </div>
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
                    <p class="theme-section-title text-sm">
                      {{ job.content_version?.version_number ?? 'Unversioned import' }}
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
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { RefreshCw, Upload } from 'lucide-vue-next';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import AppSelect from '@/components/app/AppSelect.vue';
import { useImportJobsController } from '@/modules/import-jobs/composables/useImportJobsController';

const {
  pickerTemplateId,
  pickerMode,
  contentVersionBase,
  contentVersionDescription,
  currentContentVersion,
  pickedFiles,
  errorMessage,
  jobs,
  isRefreshing,
  creatingJob,
  cancellingJobIds,
  lastRefreshedAt,
  templates,
  queuedCount,
  runningCount,
  cancelingCount,
  completedCount,
  failedCount,
  cancelledCount,
  contentVersionBaseError,
  hasValidVersionInput,
  submitButtonLabel,
  loadJobs,
  createJobFromPicker,
  cancelJob,
  onSingleFileSelected,
  onDirectorySelected,
  canCancel,
  progressPercent,
  statusClass,
  progressClass,
  formatTimestamp,
} = useImportJobsController();

const templateOptions = computed(() =>
  templates.value.map((item) => ({
    value: item.key,
    label: `${item.label} (${item.key})`,
  })),
);

const pickerModeOptions = [
  { value: 'single', label: 'Single file' },
  { value: 'directory', label: 'Directory' },
] as const;
</script>
