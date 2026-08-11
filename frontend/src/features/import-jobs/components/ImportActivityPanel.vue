<template>
  <section data-testid="import-activity-panel">
    <div class="space-y-3">
      <div>
        <h3 class="theme-section-title text-base font-semibold">
          Import activity
        </h3>
        <p class="theme-section-muted mt-1 text-sm">
          {{ queuedCount }} queued · {{ runningCount + cancelingCount }} active
          <span v-if="lastRefreshedAt"> · Updated {{ lastRefreshedAt }}</span>
        </p>
      </div>
      <div
        class="flex flex-nowrap items-center gap-2"
        data-testid="import-activity-actions"
      >
        <button
          class="btn-secondary inline-flex shrink-0 items-center gap-2 whitespace-nowrap px-3 py-2 text-xs"
          type="button"
          :disabled="refreshing"
          aria-label="Refresh import activity"
          @click="emit('refresh')"
        >
          <RefreshCw
            class="h-3.5 w-3.5"
            :class="refreshing ? 'animate-spin' : ''"
          />
          {{ refreshing ? 'Refreshing…' : 'Refresh' }}
        </button>
        <RouterLink
          class="btn-secondary inline-flex shrink-0 items-center gap-2 whitespace-nowrap px-3 py-2 text-xs"
          to="/operations#queue-imports"
        >
          <ExternalLink class="h-3.5 w-3.5" />
          Full history
        </RouterLink>
      </div>
    </div>

    <p
      v-if="errorMessage"
      class="theme-alert-danger mt-5 text-sm"
      role="alert"
    >
      {{ errorMessage }}
    </p>

    <section
      v-if="selectedJobDetail || detailLoading"
      class="theme-divider mt-5 space-y-3 border-t pt-5"
      aria-live="polite"
    >
      <p
        v-if="detailLoading"
        class="theme-section-muted text-sm"
      >
        Loading import details…
      </p>
      <template v-else-if="selectedJobDetail">
        <div>
          <h4 class="theme-section-title text-sm font-semibold">
            Import details
          </h4>
          <p class="theme-section-muted mt-1 text-xs">
            {{ selectedJobDetail.card_pool === 'game_master' ? 'Game Master' : 'Player' }} ·
            {{ selectedJobDetail.card_role_mode }}
          </p>
        </div>
        <div class="space-y-3">
          <article
            v-for="item in selectedJobDetail.items"
            :key="item.id"
            class="theme-muted-panel space-y-2 p-3"
          >
            <p class="theme-section-title truncate text-sm font-medium">
              {{ item.source_file }}
            </p>
            <p class="theme-section-muted text-xs">
              {{
                item.resolved_card_roles.length > 0
                  ? item.resolved_card_roles.join(', ')
                  : 'Standard — no special roles'
              }}
            </p>
            <dl class="theme-section-muted grid gap-1 text-xs">
              <div
                v-for="entry in getInferenceEvidence(item)"
                :key="entry.label"
                class="flex flex-wrap gap-x-1"
              >
                <dt class="font-semibold">
                  {{ entry.label }}:
                </dt>
                <dd>{{ entry.value }}</dd>
              </div>
            </dl>
            <div
              v-for="warning in item.warnings"
              :key="warning.code"
              class="theme-alert-warning text-xs"
            >
              <p>{{ warning.message }}</p>
              <dl
                v-if="getWarningEvidence(warning).length > 0"
                class="mt-1 grid gap-1"
              >
                <div
                  v-for="entry in getWarningEvidence(warning)"
                  :key="entry.label"
                  class="flex flex-wrap gap-x-1"
                >
                  <dt class="font-semibold">
                    {{ entry.label }}:
                  </dt>
                  <dd>{{ entry.value }}</dd>
                </div>
              </dl>
              <RouterLink
                v-if="warning.code === 'card_classification_mismatch' && item.card_tab_url"
                class="mt-1 inline-flex font-semibold underline"
                :to="item.card_tab_url"
              >
                Review card classification
              </RouterLink>
            </div>
          </article>
        </div>
      </template>
    </section>

    <div
      class="theme-divider mt-5 border-t"
    >
      <section
        class="pt-5"
        aria-labelledby="active-imports-heading"
      >
        <div class="flex items-center gap-2">
          <Activity class="theme-section-muted h-4 w-4" />
          <h4
            id="active-imports-heading"
            class="theme-section-title text-sm font-semibold"
          >
            Active imports
          </h4>
        </div>

        <div
          v-if="!activeLoaded"
          class="animate-pulse space-y-3 py-4"
          aria-label="Loading active imports"
        >
          <div class="h-4 w-24 rounded bg-[var(--color-surface-muted)]" />
          <div class="h-4 w-2/3 rounded bg-[var(--color-surface-muted)]" />
          <div class="h-1.5 w-full rounded bg-[var(--color-surface-muted)]" />
        </div>

        <p
          v-else-if="activeJobs.length === 0"
          class="theme-section-muted py-4 text-sm"
        >
          No active imports.
        </p>

        <div
          v-else
          class="mt-3"
        >
          <article
            v-for="job in activeJobs"
            :key="job.id"
            class="theme-divider space-y-3 border-b py-4 first:pt-1 last:border-b-0"
          >
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0 space-y-1.5">
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-[0.68rem] font-semibold uppercase tracking-[0.14em]"
                  :class="getImportJobStatusClass(job.status)"
                >
                  {{ job.status }}
                </span>
                <p class="theme-section-title text-sm font-semibold leading-5">
                  {{ job.template_id }} · {{ job.content_version?.version_number ?? 'Unversioned' }}
                </p>
                <p class="theme-section-muted text-xs">
                  {{ job.card_pool === 'game_master' ? 'Game Master' : 'Player' }} ·
                  {{
                    job.card_role_mode === 'automatic'
                      ? 'Automatic roles'
                      : job.card_role_override.length > 0
                        ? `Override: ${job.card_role_override.join(', ')}`
                        : 'Override: Standard'
                  }}
                </p>
              </div>
              <span class="theme-section-muted shrink-0 text-xs">
                {{ job.processed_items }}/{{ job.total_items }}
              </span>
            </div>

            <div
              class="theme-card-frame-muted h-1.5 overflow-hidden rounded-full"
              role="progressbar"
              :aria-valuenow="getImportJobProgressPercent(job)"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <div
                class="h-full rounded-full transition-all"
                :class="getImportJobProgressClass(job.status)"
                :style="{ width: `${getImportJobProgressPercent(job)}%` }"
              />
            </div>

            <div class="flex items-center justify-between gap-3">
              <span class="theme-section-muted text-xs">
                Updated {{ formatImportJobTimestamp(job.updated_at) }}
              </span>
              <div class="flex items-center gap-2">
                <button
                  class="btn-secondary shrink-0 rounded-full px-2.5 py-1 text-xs"
                  type="button"
                  @click="emit('view', job.id)"
                >
                  Details
                </button>
                <button
                  v-if="canCancelImportJob(job)"
                  class="btn-danger-secondary shrink-0 rounded-full px-2.5 py-1 text-xs"
                  type="button"
                  :disabled="cancellingJobIds.has(job.id)"
                  @click="emit('cancel', job.id)"
                >
                  {{ cancellingJobIds.has(job.id) ? 'Interrupting…' : 'Interrupt' }}
                </button>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section
        class="theme-divider mt-2 border-t pt-5"
        aria-labelledby="recent-imports-heading"
      >
        <h4
          id="recent-imports-heading"
          class="theme-section-title text-sm font-semibold"
        >
          Recently finished
        </h4>
        <p class="theme-section-muted mt-1 text-xs">
          Latest completed, failed, or cancelled work.
        </p>

        <div
          v-if="!historyLoaded"
          class="animate-pulse space-y-3 py-4"
          aria-label="Loading recent import history"
        >
          <div class="h-4 w-28 rounded bg-[var(--color-surface-muted)]" />
          <div class="h-4 w-3/4 rounded bg-[var(--color-surface-muted)]" />
          <div class="h-1.5 w-full rounded bg-[var(--color-surface-muted)]" />
        </div>

        <p
          v-else-if="recentJobs.length === 0"
          class="theme-section-muted py-4 text-sm"
        >
          No recent import history.
        </p>

        <div
          v-else
          class="mt-3"
        >
          <article
            v-for="job in recentJobs"
            :key="job.id"
            class="theme-divider space-y-2.5 border-b py-4 first:pt-1 last:border-b-0"
          >
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0 space-y-1.5">
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-[0.68rem] font-semibold uppercase tracking-[0.14em]"
                  :class="getImportJobStatusClass(job.status)"
                >
                  {{ job.status }}
                </span>
                <p class="theme-section-title text-sm font-semibold leading-5">
                  {{ job.title }}
                </p>
              </div>
              <span
                v-if="job.progress_current !== null && job.progress_total !== null"
                class="theme-section-muted shrink-0 text-xs"
              >
                {{ job.progress_current }}/{{ job.progress_total }}
              </span>
            </div>

            <div
              v-if="getOperationsItemProgressPercent(job) !== null"
              class="theme-card-frame-muted h-1.5 overflow-hidden rounded-full"
              role="progressbar"
              :aria-valuenow="getOperationsItemProgressPercent(job) ?? undefined"
              aria-valuemin="0"
              aria-valuemax="100"
            >
              <div
                class="h-full rounded-full"
                :class="getImportJobProgressClass(job.status)"
                :style="{ width: `${getOperationsItemProgressPercent(job)}%` }"
              />
            </div>

            <span class="theme-section-muted block text-xs">
              Updated {{ formatImportJobTimestamp(job.updated_at) }}
            </span>
            <button
              class="btn-secondary rounded-full px-2.5 py-1 text-xs"
              type="button"
              @click="emit('view', job.id)"
            >
              Details
            </button>
          </article>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Activity, ExternalLink, RefreshCw } from 'lucide-vue-next';
import { RouterLink } from 'vue-router';
import type { OperationsQueueItem } from '@/domain/operations/types';
import type {
  ImportJob,
  ImportJobDetail,
  ImportJobItem,
  ImportWarning,
} from '@/features/import-jobs/types';
import {
  canCancelImportJob,
  formatImportJobTimestamp,
  getImportJobProgressClass,
  getImportJobProgressPercent,
  getImportJobStatusClass,
  getOperationsItemProgressPercent,
} from '@/features/import-jobs/utils/importJobUtils';

defineProps<{
  activeJobs: ImportJob[];
  recentJobs: OperationsQueueItem[];
  activeLoaded: boolean;
  historyLoaded: boolean;
  refreshing: boolean;
  errorMessage: string;
  queuedCount: number;
  runningCount: number;
  cancelingCount: number;
  cancellingJobIds: Set<string>;
  lastRefreshedAt: string | null;
  selectedJobDetail: ImportJobDetail | null;
  detailLoading: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
  cancel: [jobId: string];
  view: [jobId: string];
}>();

type EvidenceEntry = { label: string; value: string };

const asRecord = (value: unknown): Record<string, unknown> | null =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;

const asStringArray = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];

const formatRole = (role: string): string => role.charAt(0).toUpperCase() + role.slice(1);
const formatRoles = (value: unknown): string => {
  const roles = asStringArray(value);
  return roles.length > 0 ? roles.map(formatRole).join(', ') : 'Standard';
};
const formatPool = (value: unknown): string =>
  value === 'game_master' ? 'Game Master' : value === 'player' ? 'Player' : 'Unknown';

const formatClassification = (value: unknown): string | null => {
  const classification = asRecord(value);
  if (!classification) return null;
  return `${formatPool(classification.card_pool)} · ${formatRoles(classification.card_roles)}`;
};

const getInferenceEvidence = (item: ImportJobItem): EvidenceEntry[] => {
  const evidence = item.card_role_inference;
  const mode = evidence.mode === 'override' ? 'Manual override' : 'Automatic';
  const entries: EvidenceEntry[] = [{ label: 'Resolution', value: mode }];
  const templateRoles = asStringArray(evidence.template_roles);
  const matchedTags = asStringArray(evidence.matched_tag_keys);
  const overrideRoles = asStringArray(evidence.override_roles);

  if (templateRoles.length > 0) {
    entries.push({ label: 'Template hints', value: templateRoles.map(formatRole).join(', ') });
  }
  if (matchedTags.length > 0) {
    entries.push({ label: 'Matched tags', value: matchedTags.join(', ') });
  }
  if (evidence.mode === 'override') {
    entries.push({ label: 'Override roles', value: formatRoles(overrideRoles) });
  }
  if (templateRoles.length === 0 && matchedTags.length === 0 && evidence.mode !== 'override') {
    entries.push({ label: 'Role signals', value: 'None matched' });
  }
  return entries;
};

const getWarningEvidence = (warning: ImportWarning): EvidenceEntry[] => {
  const details = warning.details;
  if (!details) return [];
  const entries: EvidenceEntry[] = [];
  const labels: Array<[string, string]> = [
    ['inferred', 'Inferred'],
    ['existing', 'Existing'],
    ['queued', 'Queued'],
    ['live', 'Live'],
  ];
  for (const [key, label] of labels) {
    const value = formatClassification(details[key]);
    if (value) entries.push({ label, value });
  }
  return entries;
};
</script>
