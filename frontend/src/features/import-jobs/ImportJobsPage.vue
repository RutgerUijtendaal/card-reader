<template>
  <section class="flex flex-col gap-6">
    <AppPageHeader
      :icon="Upload"
      title="Imports"
      subtitle="Configure card image imports and follow their progress."
      title-tag="h2"
      title-class="text-xl"
    />

    <AppPageLayout
      columns="one"
      main-class="w-full max-w-7xl justify-self-center"
    >
      <div class="grid xl:grid-cols-[minmax(0,1.55fr)_minmax(22rem,1fr)]">
        <div class="min-w-0 xl:pr-10">
          <div
            v-if="!formLoaded"
            class="space-y-7"
            aria-label="Loading import options"
          >
            <div class="space-y-3">
              <div class="h-7 w-36 animate-pulse rounded bg-[var(--color-surface-muted)]" />
              <div
                class="h-4 w-80 max-w-full animate-pulse rounded bg-[var(--color-surface-muted)]"
              />
            </div>
            <div
              v-for="index in 3"
              :key="index"
              class="theme-divider space-y-4 border-t pt-6"
            >
              <div class="h-5 w-32 animate-pulse rounded bg-[var(--color-surface-muted)]" />
              <div class="grid gap-4 sm:grid-cols-2">
                <div class="h-11 animate-pulse rounded-lg bg-[var(--color-surface-muted)]" />
                <div class="h-11 animate-pulse rounded-lg bg-[var(--color-surface-muted)]" />
              </div>
            </div>
          </div>

          <form
            v-else
            id="import-job-form"
            @submit.prevent="createJobFromPicker"
          >
            <div class="space-y-2">
              <h3 class="theme-section-title text-xl font-semibold">
                New import
              </h3>
              <p class="theme-section-muted max-w-2xl text-sm leading-6">
                Set the card context, choose a content version, and add the source images to
                process.
              </p>
            </div>

            <AppFormSection
              class="mt-7"
              title="Card setup"
              description="Choose how the uploaded cards should be interpreted."
            >
              <div class="grid gap-5 md:grid-cols-2">
                <label class="field-label">
                  Template
                  <AppSelect
                    v-model="pickerTemplateId"
                    :options="templateOptions"
                    :disabled="formLocked"
                    required
                  />
                </label>
                <label class="field-label">
                  Card pool
                  <AppSelect
                    v-model="cardPool"
                    :options="cardPoolOptions"
                    :disabled="formLocked"
                    required
                  />
                </label>
                <fieldset class="theme-divider space-y-3 border-t pt-4 md:col-span-2">
                  <legend class="field-label">
                    Card roles
                  </legend>
                  <div class="flex flex-wrap gap-3">
                    <label class="theme-section-title inline-flex items-center gap-2 text-sm">
                      <input
                        v-model="cardRoleMode"
                        type="radio"
                        value="automatic"
                        :disabled="formLocked"
                      >
                      Automatic
                    </label>
                    <label class="theme-section-title inline-flex items-center gap-2 text-sm">
                      <input
                        v-model="cardRoleMode"
                        type="radio"
                        value="override"
                        :disabled="formLocked"
                      >
                      Override
                    </label>
                  </div>
                  <p class="theme-section-muted mt-1 text-sm">
                    Automatic combines role hints from the template with detected card metadata.
                  </p>
                  <div
                    v-if="cardRoleMode === 'override'"
                    class="flex flex-wrap gap-3"
                  >
                    <label
                      v-for="option in cardRoleOptions"
                      :key="option.value"
                      class="theme-section-title inline-flex items-center gap-2 text-sm"
                    >
                      <input
                        v-model="cardRoleOverride"
                        type="checkbox"
                        :value="option.value"
                        :disabled="formLocked"
                      >
                      {{ option.label }}
                    </label>
                    <span
                      v-if="cardRoleOverride.length === 0"
                      class="theme-section-muted basis-full text-sm"
                    >
                      Standard — no special roles
                    </span>
                  </div>
                </fieldset>
              </div>

              <p
                v-if="templates.length === 0"
                class="theme-alert-warning mt-4"
              >
                No templates available. Add one in Admin &gt; Templates first.
              </p>
            </AppFormSection>

            <AppFormSection
              class="mt-7"
              title="Content version"
              description="Group the imported card changes under a named content release."
            >
              <div class="grid gap-5 md:grid-cols-2">
                <div
                  class="theme-muted-panel py-3 md:col-span-2"
                  data-testid="current-content-version"
                >
                  <div class="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                    <span class="theme-kicker text-xs font-semibold uppercase tracking-[0.18em]">
                      Current release
                    </span>
                    <span class="theme-section-title text-sm font-semibold">
                      {{
                        currentContentVersionLoaded
                          ? currentContentVersion?.version_number ?? 'No version yet'
                          : 'Loading…'
                      }}
                    </span>
                  </div>
                  <p
                    v-if="currentContentVersion"
                    class="theme-section-muted mt-2 text-sm leading-5"
                  >
                    {{ currentContentVersion.description }}
                  </p>
                </div>

                <div
                  class="grid gap-4 md:col-span-2 md:grid-cols-[minmax(0,16rem)_minmax(0,1fr)] md:items-start"
                  data-testid="new-version-row"
                >
                  <label class="field-label">
                    New version
                    <input
                      id="content-version-base"
                      v-model="contentVersionBase"
                      class="input-base"
                      type="text"
                      inputmode="numeric"
                      pattern="[0-9]+\.[0-9]+"
                      placeholder="14.1"
                      autocomplete="off"
                      :disabled="formLocked"
                      :aria-invalid="contentVersionBaseError.length > 0"
                      aria-describedby="content-version-base-help content-version-patch-help"
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

                  <div class="flex gap-3 md:pt-7">
                    <Info class="theme-kicker mt-0.5 h-4 w-4 shrink-0" />
                    <div class="space-y-1">
                      <p class="theme-section-title text-sm font-medium">
                        Patch number is automatic
                      </p>
                      <p
                        id="content-version-patch-help"
                        class="theme-section-muted text-xs leading-5"
                      >
                        <template v-if="currentContentVersion">
                          Keep {{ currentContentVersion.base_version }} to create the next available
                          patch after {{ currentContentVersion.version_number }}. A major.minor with
                          no previous releases starts at patch 0.
                        </template>
                        <template v-else>
                          The first release for a major.minor starts at patch 0. Later imports using
                          the same value receive the next available patch.
                        </template>
                      </p>
                    </div>
                  </div>
                </div>

                <label class="field-label md:col-span-2">
                  Description
                  <textarea
                    v-model="contentVersionDescription"
                    class="input-base min-h-28 resize-y"
                    :disabled="formLocked"
                    required
                  />
                </label>
              </div>
            </AppFormSection>

            <AppFormSection
              class="mt-7"
              title="Source images"
              description="Add one image or a folder of supported card images."
            >
              <div :class="formLocked ? 'pointer-events-none opacity-60' : ''">
                <ImportSourcePicker
                  :files="pickedFiles"
                  :reset-key="fileInputKey"
                  @select="setPickedFiles"
                  @clear="clearPickedFiles"
                />
              </div>
            </AppFormSection>

            <div
              class="theme-divider mt-7 flex flex-col gap-4 border-t pt-6 sm:flex-row sm:items-center sm:justify-between"
            >
              <p
                v-if="formErrorMessage"
                class="theme-alert-danger text-sm"
                role="alert"
              >
                {{ formErrorMessage }}
              </p>
              <span
                v-else
                class="theme-section-muted text-sm"
              >
                The import will be added to the parser queue.
              </span>
              <button
                v-if="createState.phase === 'uncertain'"
                class="btn-secondary"
                type="button"
                @click="abandonPendingAttempt"
              >
                Abandon attempt and edit
              </button>
              <button
                class="btn-primary w-full justify-center sm:w-auto sm:min-w-44"
                type="submit"
                :disabled="
                  pickedFiles.length === 0 ||
                    templates.length === 0 ||
                    !hasValidVersionInput ||
                    creatingJob || createState.phase === 'reconciling'
                "
              >
                {{ submitButtonLabel }}
              </button>
            </div>
          </form>
        </div>

        <div
          class="theme-divider mt-8 border-t pt-8 xl:mt-0 xl:border-l xl:border-t-0 xl:pl-10 xl:pt-0"
        >
          <ImportActivityPanel
            :active-jobs="activeJobs"
            :recent-jobs="recentJobs"
            :active-loaded="activeJobsLoaded"
            :history-loaded="historyLoaded"
            :refreshing="isRefreshing"
            :error-message="activityErrorMessage"
            :queued-count="queuedCount"
            :running-count="runningCount"
            :canceling-count="cancelingCount"
            :cancelling-job-ids="cancellingJobIds"
            :last-refreshed-at="lastRefreshedAt"
            :selected-job-detail="selectedJobDetail"
            :detail-loading="detailLoading"
            @refresh="refreshActivity"
            @cancel="cancelJob"
            @view="viewJobDetail"
            @close-detail="closeJobDetail"
          />
        </div>
      </div>
    </AppPageLayout>
  </section>
</template>

<script setup lang="ts">
import { CARD_ROLE_OPTIONS } from '@/domain/cards/cardRoles';
import { CARD_POOL_OPTIONS } from '@/domain/cards/cardPools';
import { Info, Upload } from 'lucide-vue-next';
import { computed } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import ImportActivityPanel from '@/features/import-jobs/components/ImportActivityPanel.vue';
import ImportSourcePicker from '@/features/import-jobs/components/ImportSourcePicker.vue';
import { useImportJobsController } from '@/features/import-jobs/composables/useImportJobsController';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import AppFormSection from '@/shared/components/app/AppFormSection.vue';
import AppSelect from '@/shared/components/app/AppSelect.vue';

const {
  pickerTemplateId,
  cardPool,
  cardRoleMode,
  cardRoleOverride,
  contentVersionBase,
  contentVersionDescription,
  currentContentVersion,
  pickedFiles,
  fileInputKey,
  formErrorMessage,
  activityErrorMessage,
  activeJobs,
  recentJobs,
  formLoaded,
  currentContentVersionLoaded,
  activeJobsLoaded,
  historyLoaded,
  isRefreshing,
  creatingJob,
  cancellingJobIds,
  lastRefreshedAt,
  templates,
  selectedJobDetail,
  detailLoading,
  queuedCount,
  runningCount,
  cancelingCount,
  contentVersionBaseError,
  hasValidVersionInput,
  submitButtonLabel,
  formLocked,
  hasUnresolvedCreateAttempt,
  createState,
  refreshActivity,
  createJobFromPicker,
  cancelJob,
  viewJobDetail,
  closeJobDetail,
  setPickedFiles,
  clearPickedFiles,
  abandonPendingAttempt,
} = useImportJobsController();

const templateOptions = computed(() =>
  templates.value.map((item) => ({ value: item.key, label: `${item.label} (${item.key})` })),
);
const cardPoolOptions = CARD_POOL_OPTIONS;
const cardRoleOptions = CARD_ROLE_OPTIONS;

onBeforeRouteLeave(() => {
  if (!hasUnresolvedCreateAttempt.value) return true;
  if (createState.value.phase !== 'uncertain') return false;
  return globalThis.confirm(
    'The outcome of this import is still uncertain. Leaving now discards the locked retry details and can cause a duplicate import. Leave anyway?',
  );
});
</script>
