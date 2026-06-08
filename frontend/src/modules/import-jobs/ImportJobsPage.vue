<template>
  <section class="flex flex-col gap-6">
    <AppPageHeader
      :icon="Upload"
      title="Import Jobs"
      subtitle="Queue card image batches, monitor parser throughput, and interrupt active jobs."
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <div class="flex flex-wrap items-center justify-end gap-2">
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

    <AppPageLayout
      columns="one"
      root-class="app-page-layout-standard"
    >
      <template #aside>
        <AppStickyAside>
          <form
            id="import-job-form"
            class="space-y-5"
            @submit.prevent="createJobFromPicker"
          >
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
          </form>

          <template #footer>
            <div class="space-y-3">
              <p
                v-if="errorMessage"
                class="theme-alert-danger"
              >
                {{ errorMessage }}
              </p>

              <button
                class="btn-primary w-full justify-center"
                type="submit"
                form="import-job-form"
                :disabled="pickedFiles.length === 0 || templates.length === 0 || !hasValidVersionInput || creatingJob"
              >
                {{ submitButtonLabel }}
              </button>
            </div>
          </template>
        </AppStickyAside>
      </template>

      <section>
        <div class="theme-divider flex flex-wrap items-start justify-between gap-4 border-b px-1 pb-4">
          <div class="min-w-0 space-y-1">
            <h3 class="theme-section-title text-base font-semibold">
              Queue Monitor
            </h3>
            <p class="theme-section-muted text-sm">
              Parser jobs ordered by the latest queue activity.
            </p>
            <p class="theme-section-muted text-sm">
              {{ isRefreshing ? 'Refreshing live status...' : lastRefreshedAt ? `Last update ${lastRefreshedAt}.` : 'Live status idle.' }}
            </p>
          </div>

          <div class="shrink-0">
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
          </div>
        </div>

        <div class="pt-5">
          <div
            v-if="!jobsLoaded"
            class="theme-divider"
          >
            <article
              v-for="index in 4"
              :key="`import-job-loading-${index}`"
              class="import-job-row theme-divider py-3"
            >
              <div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-stretch">
                <div class="min-w-0 space-y-2 pr-2">
                  <div class="flex items-center gap-2">
                    <span class="h-6 w-24 animate-pulse rounded-full bg-[var(--color-surface-muted)]" />
                    <span class="h-3 w-48 animate-pulse rounded bg-[var(--color-surface-muted)]" />
                  </div>
                  <div class="space-y-2">
                    <div class="h-4 w-36 animate-pulse rounded bg-[var(--color-surface-muted)]" />
                    <div class="h-4 w-28 animate-pulse rounded bg-[var(--color-surface-muted)]" />
                    <div class="h-4 w-full animate-pulse rounded bg-[var(--color-surface-muted)]" />
                  </div>
                </div>

                <div class="flex h-full flex-col gap-3 md:items-end md:justify-between">
                  <div class="grid grid-cols-2 gap-x-5 gap-y-1 md:text-right">
                    <div class="space-y-2">
                      <div class="h-3 w-16 animate-pulse rounded bg-[var(--color-surface-muted)]" />
                      <div class="h-4 w-24 animate-pulse rounded bg-[var(--color-surface-muted)]" />
                    </div>
                    <div class="space-y-2">
                      <div class="h-3 w-16 animate-pulse rounded bg-[var(--color-surface-muted)]" />
                      <div class="h-4 w-24 animate-pulse rounded bg-[var(--color-surface-muted)]" />
                    </div>
                  </div>
                  <div class="flex w-full items-center gap-3 md:w-72">
                    <div class="h-4 w-12 shrink-0 animate-pulse rounded bg-[var(--color-surface-muted)]" />
                    <div class="h-2 w-full min-w-40 animate-pulse rounded-full bg-[var(--color-surface-muted)]" />
                  </div>
                </div>
              </div>
            </article>
          </div>

          <div
            v-else-if="jobs.length === 0"
            class="theme-section-muted py-10 text-sm"
          >
            No import jobs yet.
          </div>

          <div
            v-else
            class="theme-divider"
          >
            <article
              v-for="job in jobs"
              :key="job.id"
              class="import-job-row theme-divider py-3"
            >
              <div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-stretch">
                <div class="min-w-0 space-y-2 pr-2">
                  <div class="flex flex-wrap items-center gap-2">
                    <span
                      class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.16em]"
                      :class="statusClass(job.status)"
                    >
                      {{ job.status }}
                    </span>
                    <span
                      class="theme-kicker max-w-full truncate text-xs sm:max-w-[18rem]"
                      :title="job.id"
                    >
                      {{ job.id }}
                    </span>
                  </div>
                  <div class="space-y-1">
                    <p class="theme-section-title text-sm font-semibold">
                      {{ job.template_id }}
                    </p>
                    <p class="theme-section-title text-sm">
                      {{ job.content_version?.version_number ?? 'Unversioned import' }}
                    </p>
                    <p
                      class="theme-section-muted truncate text-sm leading-5"
                      :title="job.source_path"
                    >
                      {{ job.source_path }}
                    </p>
                  </div>
                </div>

                <div class="flex h-full flex-col items-start gap-3 md:items-end md:justify-between md:pl-1">
                  <div class="flex flex-col items-start gap-3 md:items-end">
                    <dl class="theme-section-muted grid grid-cols-2 gap-x-5 gap-y-1 text-left text-sm md:text-right">
                      <div>
                        <dt class="theme-kicker text-[11px] uppercase tracking-[0.16em]">
                          Created
                        </dt>
                        <dd class="theme-section-title mt-1">
                          {{ formatTimestamp(job.created_at) }}
                        </dd>
                      </div>
                      <div>
                        <dt class="theme-kicker text-[11px] uppercase tracking-[0.16em]">
                          Updated
                        </dt>
                        <dd class="theme-section-title mt-1">
                          {{ formatTimestamp(job.updated_at) }}
                        </dd>
                      </div>
                    </dl>

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

                  <div class="flex w-full items-center gap-3 md:w-72">
                    <span class="theme-section-muted shrink-0 text-sm">
                      {{ job.processed_items }}/{{ job.total_items }}
                    </span>
                    <div class="theme-card-frame-muted h-2 flex-1 rounded-full">
                      <div
                        class="h-full rounded-full transition-all"
                        :class="progressClass(job.status)"
                        :style="{ width: `${progressPercent(job)}%` }"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </div>
      </section>
    </AppPageLayout>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { RefreshCw, Upload } from 'lucide-vue-next';
import AppPageLayout from '@/components/app/AppPageLayout.vue';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import AppSelect from '@/components/app/AppSelect.vue';
import AppStickyAside from '@/components/app/AppStickyAside.vue';
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
  jobsLoaded,
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

<style scoped>
.import-job-row + .import-job-row {
  border-top-width: 1px;
}
</style>
