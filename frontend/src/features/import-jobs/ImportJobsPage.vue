<template>
  <section class="flex flex-col gap-6">
    <AppPageHeader
      :icon="Upload"
      title="Imports"
      subtitle="Upload card images and manage imports that are still in progress."
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <RouterLink
          class="btn-secondary inline-flex items-center gap-2"
          to="/operations#queue-imports"
        >
          <Activity class="h-4 w-4" />
          View queue history
        </RouterLink>
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
                New import
              </h3>
              <p class="theme-section-muted text-sm">
                Upload one file or a folder into the parser queue.
              </p>
            </div>

            <div class="theme-muted-panel rounded-xl px-4 py-4">
              <div class="theme-kicker text-xs font-semibold uppercase tracking-[0.18em]">
                Current version
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
                <span class="theme-kicker text-xs font-semibold uppercase tracking-[0.16em]">Selection</span>
                <span class="theme-section-title text-sm font-semibold">
                  {{ pickedFiles.length }} file{{ pickedFiles.length === 1 ? '' : 's' }}
                </span>
              </div>

              <p
                v-if="templates.length === 0"
                class="theme-alert-warning"
              >
                No templates available. Add one in Admin &gt; Templates first.
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
          <div class="space-y-1">
            <h3 class="theme-section-title text-base font-semibold">
              Active imports
            </h3>
            <p class="theme-section-muted text-sm">
              {{ queuedCount }} queued · {{ runningCount + cancelingCount }} active
            </p>
            <p class="theme-section-muted text-sm">
              {{ lastRefreshedAt ? `Last update ${lastRefreshedAt}.` : 'Loading current work…' }}
            </p>
          </div>
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
            {{ isRefreshing ? 'Refreshing…' : 'Refresh' }}
          </button>
        </div>

        <div
          v-if="!jobsLoaded"
          class="theme-divider"
        >
          <article
            v-for="index in 3"
            :key="index"
            class="theme-divider space-y-3 py-5"
          >
            <div class="h-5 w-24 animate-pulse rounded bg-[var(--color-surface-muted)]" />
            <div class="h-4 w-3/4 animate-pulse rounded bg-[var(--color-surface-muted)]" />
            <div class="h-2 w-full animate-pulse rounded bg-[var(--color-surface-muted)]" />
          </article>
        </div>

        <div
          v-else-if="jobs.length === 0"
          class="py-10"
        >
          <p class="theme-section-title text-sm font-semibold">
            No active imports
          </p>
          <p class="theme-section-muted mt-1 text-sm">
            Queue history and completed work remain available in Operations.
          </p>
        </div>

        <div
          v-else
          class="theme-divider"
        >
          <article
            v-for="job in jobs"
            :key="job.id"
            class="theme-divider border-b py-5"
          >
            <div class="grid gap-5 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
              <div class="min-w-0 space-y-2">
                <span
                  class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.16em]"
                  :class="statusClass(job.status)"
                >
                  {{ job.status }}
                </span>
                <p class="theme-section-title text-sm font-semibold">
                  {{ job.template_id }} · {{ job.content_version?.version_number ?? 'Unversioned' }}
                </p>
                <p
                  class="theme-section-muted truncate text-sm"
                  :title="job.source_path"
                >
                  {{ job.source_path }}
                </p>
                <div class="flex items-center gap-3">
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
              <div class="flex flex-col items-start gap-3 md:items-end">
                <span class="theme-section-muted text-sm">Updated {{ formatTimestamp(job.updated_at) }}</span>
                <button
                  v-if="canCancel(job)"
                  class="btn-danger-secondary rounded-full px-3 py-1.5"
                  type="button"
                  :disabled="cancellingJobIds.has(job.id)"
                  @click="cancelJob(job.id)"
                >
                  {{ cancellingJobIds.has(job.id) ? 'Interrupting…' : 'Interrupt job' }}
                </button>
              </div>
            </div>
          </article>
        </div>
      </section>
    </AppPageLayout>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Activity, RefreshCw, Upload } from 'lucide-vue-next';
import { RouterLink } from 'vue-router';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import AppSelect from '@/shared/components/app/AppSelect.vue';
import AppStickyAside from '@/shared/components/app/AppStickyAside.vue';
import { useImportJobsController } from '@/features/import-jobs/composables/useImportJobsController';

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
  templates.value.map((item) => ({ value: item.key, label: `${item.label} (${item.key})` })),
);

const pickerModeOptions = [
  { value: 'single', label: 'Single file' },
  { value: 'directory', label: 'Directory' },
] as const;
</script>
