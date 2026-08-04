<template>
  <section class="theme-divider border-t">
    <div
      v-if="loading"
      class="theme-section-muted py-6 text-sm"
    >
      Loading developer-data bundle information…
    </div>

    <div
      v-else-if="errorMessage"
      class="py-6"
      role="alert"
    >
      <p class="theme-section-title text-sm font-semibold">
        Developer data could not be loaded
      </p>
      <p class="theme-section-muted mt-1 text-sm">
        {{ errorMessage }}
      </p>
      <button
        type="button"
        class="btn-secondary mt-4"
        @click="loadBundle"
      >
        Try again
      </button>
    </div>

    <div
      v-else-if="!bundle"
      class="py-6"
    >
      <p class="theme-section-title text-sm font-semibold">
        No developer bundle is currently available
      </p>
      <p class="theme-section-muted mt-1 text-sm">
        A maintainer must publish a reviewed bundle before browser downloads or bootstrap codes can be used.
      </p>
    </div>

    <template v-else>
      <div class="grid gap-4 py-5 sm:grid-cols-2">
        <div>
          <p class="theme-section-muted text-xs font-semibold uppercase tracking-wide">
            Bundle version
          </p>
          <p class="theme-section-title mt-1 font-mono text-sm">
            {{ bundle.bundle_version }}
          </p>
        </div>
        <div>
          <p class="theme-section-muted text-xs font-semibold uppercase tracking-wide">
            Archive
          </p>
          <p class="theme-section-title mt-1 text-sm">
            {{ formatBytes(bundle.size_bytes) }} · format {{ bundle.format_version }}
          </p>
        </div>
        <div class="sm:col-span-2">
          <p class="theme-section-muted text-xs font-semibold uppercase tracking-wide">
            Created
          </p>
          <p class="theme-section-title mt-1 text-sm">
            {{ formatDate(bundle.created_at) }}
          </p>
        </div>
        <div class="sm:col-span-2">
          <p class="theme-section-muted text-xs font-semibold uppercase tracking-wide">
            SHA-256
          </p>
          <p class="theme-card-frame-muted theme-section-title mt-1 break-all rounded-lg border px-3 py-2 font-mono text-xs">
            {{ bundle.sha256 }}
          </p>
        </div>
      </div>

      <div class="theme-divider flex flex-col gap-3 border-t py-5 sm:flex-row sm:items-center">
        <div class="min-w-0 flex-1">
          <p class="theme-section-title text-sm font-semibold">
            Browser download
          </p>
          <p class="theme-section-muted mt-1 text-sm">
            Download the archive directly for offline bootstrap with <code>--archive</code>.
          </p>
        </div>
        <a
          class="btn-primary justify-center gap-2"
          :href="downloadUrl"
        >
          <Download class="h-4 w-4" />
          Download bundle
        </a>
      </div>

      <div class="theme-divider border-t py-5">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-start">
          <div class="min-w-0 flex-1">
            <p class="theme-section-title text-sm font-semibold">
              Bootstrap a clean checkout
            </p>
            <p class="theme-section-muted mt-1 text-sm">
              Generate a single-use code, then run <code>pnpm bootstrap:dev</code> locally and paste it when prompted.
            </p>
          </div>
          <button
            type="button"
            class="btn-secondary justify-center gap-2"
            :disabled="generating"
            @click="generateCode"
          >
            <KeyRound class="h-4 w-4" />
            {{ generating ? 'Generating…' : 'Generate code' }}
          </button>
        </div>

        <div
          v-if="grant"
          class="theme-card-frame-muted mt-4 rounded-xl border p-4"
        >
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
            <code class="theme-section-title min-w-0 flex-1 break-all text-lg font-semibold tracking-wider">
              {{ grant.code }}
            </code>
            <button
              type="button"
              class="btn-secondary justify-center gap-2"
              @click="copyCode"
            >
              <Check
                v-if="copied"
                class="h-4 w-4"
              />
              <Copy
                v-else
                class="h-4 w-4"
              />
              {{ copied ? 'Copied' : 'Copy code' }}
            </button>
          </div>
          <p class="theme-section-muted mt-2 text-xs">
            Expires {{ formatDate(grant.expires_at) }}. Creating another code revokes this one.
          </p>
        </div>

        <p
          v-if="grantError"
          class="mt-3 text-sm text-red-600 dark:text-red-300"
          role="alert"
        >
          {{ grantError }}
        </p>
      </div>
    </template>

    <div
      v-if="canManage"
      class="theme-divider border-t py-5"
    >
      <div class="flex flex-col gap-3 sm:flex-row sm:items-start">
        <div class="min-w-0 flex-1">
          <p class="theme-section-title text-sm font-semibold">
            Publish developer data
          </p>
          <p class="theme-section-muted mt-1 text-sm">
            Queue a sanitized build from the current production data and reviewed selection. Validation and publishing run in the background.
          </p>
        </div>
        <button
          type="button"
          class="btn-primary justify-center gap-2"
          :disabled="creatingBuild || hasActiveBuild"
          @click="createBuild"
        >
          <LoaderCircle
            v-if="creatingBuild"
            class="h-4 w-4 animate-spin"
          />
          <PackagePlus
            v-else
            class="h-4 w-4"
          />
          {{ creatingBuild ? 'Queuing…' : hasActiveBuild ? 'Build in progress' : 'Build new version' }}
        </button>
      </div>

      <p
        v-if="buildError"
        class="mt-3 text-sm text-red-600 dark:text-red-300"
        role="alert"
      >
        {{ buildError }}
      </p>

      <div
        v-if="buildsLoading"
        class="theme-section-muted mt-4 text-sm"
      >
        Loading build history…
      </div>

      <div
        v-else-if="builds.length === 0"
        class="theme-card-frame-muted theme-section-muted mt-4 rounded-xl border px-4 py-3 text-sm"
      >
        No staff-generated builds yet.
      </div>

      <div
        v-else
        class="theme-divider mt-4 border-t"
      >
        <div
          v-for="build in builds.slice(0, 8)"
          :key="build.id"
          class="theme-divider flex flex-col gap-3 border-b py-4 sm:flex-row sm:items-center"
        >
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="theme-section-title break-all font-mono text-sm font-semibold">
                {{ build.bundle_version }}
              </span>
              <span
                class="theme-pill px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
                :class="buildStatusClass(build.status)"
              >
                {{ build.status }}
              </span>
            </div>
            <p class="theme-section-muted mt-1 text-xs">
              Requested by {{ build.requested_by ?? 'a deleted user' }} · {{ formatDate(build.created_at) }}
            </p>
            <p
              v-if="build.error_message"
              class="mt-2 text-sm text-red-600 dark:text-red-300"
            >
              {{ build.error_message }}
            </p>
          </div>
          <a
            v-if="build.lock_download_url"
            class="btn-secondary shrink-0 justify-center gap-2"
            :href="developerDataLockUrl(build.lock_download_url)"
          >
            <FileDown class="h-4 w-4" />
            Download lock file
          </a>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useIntervalFn } from '@vueuse/core';
import { Check, Copy, Download, FileDown, KeyRound, LoaderCircle, PackagePlus } from 'lucide-vue-next';
import {
  createDeveloperDataBuild,
  createDeveloperDataGrant,
  developerDataDownloadUrl,
  developerDataLockUrl,
  fetchDeveloperDataBuilds,
  fetchCurrentDeveloperData,
} from '@/domain/developer-data/api';
import type {
  DeveloperDataBuild,
  DeveloperDataBuildStatus,
  DeveloperDataBundle,
  DeveloperDataGrant,
} from '@/domain/developer-data/types';

const props = defineProps<{
  canManage: boolean;
}>();

const loading = ref(true);
const generating = ref(false);
const bundle = ref<DeveloperDataBundle | null>(null);
const grant = ref<DeveloperDataGrant | null>(null);
const errorMessage = ref('');
const grantError = ref('');
const copied = ref(false);
const buildsLoading = ref(props.canManage);
const creatingBuild = ref(false);
const buildError = ref('');
const builds = ref<DeveloperDataBuild[]>([]);

const downloadUrl = computed(() =>
  bundle.value ? developerDataDownloadUrl(bundle.value.download_url) : '',
);
const hasActiveBuild = computed(() =>
  builds.value.some((build) => build.status === 'queued' || build.status === 'running'),
);

const { pause: pauseBuildPolling, resume: resumeBuildPolling } = useIntervalFn(
  () => void loadBuilds(),
  2500,
  { immediate: false },
);

const loadBundle = async (): Promise<void> => {
  loading.value = true;
  errorMessage.value = '';
  try {
    const current = await fetchCurrentDeveloperData();
    bundle.value = current.available ? current : null;
    if (!current.available && current.detail) {
      errorMessage.value = current.detail;
    }
  } catch {
    bundle.value = null;
    errorMessage.value = 'The server did not return bundle metadata.';
  } finally {
    loading.value = false;
  }
};

const generateCode = async (): Promise<void> => {
  generating.value = true;
  grantError.value = '';
  copied.value = false;
  try {
    grant.value = await createDeveloperDataGrant();
  } catch {
    grantError.value = 'A bootstrap code could not be generated. Please try again.';
  } finally {
    generating.value = false;
  }
};

const copyCode = async (): Promise<void> => {
  if (!grant.value) {
    return;
  }
  try {
    await navigator.clipboard.writeText(grant.value.code);
    copied.value = true;
  } catch {
    grantError.value = 'The code could not be copied automatically.';
  }
};

async function loadBuilds(): Promise<void> {
  if (!props.canManage) {
    return;
  }
  const previouslyActive = hasActiveBuild.value;
  try {
    const nextBuilds = await fetchDeveloperDataBuilds();
    builds.value = nextBuilds;
    buildError.value = '';
    if (previouslyActive && !hasActiveBuild.value) {
      await loadBundle();
    }
  } catch {
    buildError.value = 'Build history could not be loaded.';
  } finally {
    buildsLoading.value = false;
  }
}

const createBuild = async (): Promise<void> => {
  creatingBuild.value = true;
  buildError.value = '';
  try {
    const build = await createDeveloperDataBuild();
    builds.value = [build, ...builds.value.filter((entry) => entry.id !== build.id)];
  } catch {
    buildError.value = 'A new build could not be queued. Refresh the history and try again.';
  } finally {
    creatingBuild.value = false;
  }
};

const buildStatusClass = (status: DeveloperDataBuildStatus): string => {
  if (status === 'succeeded') {
    return 'theme-pill-success';
  }
  if (status === 'failed') {
    return 'theme-pill-danger';
  }
  return status === 'running' ? 'theme-pill-warning' : 'theme-pill-neutral';
};

const formatBytes = (value: number): string => {
  if (value < 1024 * 1024) {
    return `${Math.max(1, Math.round(value / 1024))} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
};

const formatDate = (value: string): string =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));

watch(
  hasActiveBuild,
  (active) => {
    if (active) {
      resumeBuildPolling();
    } else {
      pauseBuildPolling();
    }
  },
  { immediate: true },
);

onMounted(async () => {
  await Promise.all([loadBundle(), loadBuilds()]);
});
</script>
