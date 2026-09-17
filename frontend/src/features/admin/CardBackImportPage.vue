<template>
  <AppPageHeader
    :icon="APP_SECTION_ICONS.admin"
    title="Import card backs"
    subtitle="Add card backs to the library and optionally assign them to heroes."
    :back-to="{ path: '/admin', query: { admin_tab: 'card-backs' } }"
    back-label="Card backs"
  />
  <AppPageLayout>
    <template #aside>
      <AppStickyAside>
        <div class="space-y-4">
          <h2 class="theme-section-title font-semibold">
            Your import
          </h2>
          <dl class="space-y-2 text-sm">
            <div class="flex justify-between">
              <dt>Library only</dt><dd>{{ libraryCount }}</dd>
            </div>
            <div class="flex justify-between">
              <dt>Hero assignments</dt><dd>{{ heroCount }}</dd>
            </div>
            <div class="flex justify-between">
              <dt>Replacing overrides</dt><dd>{{ replacementCount }}</dd>
            </div>
            <div class="theme-divider flex justify-between border-t pt-2">
              <dt>Completed</dt><dd>{{ completedCount }} / {{ rows.length }}</dd>
            </div>
          </dl>
          <p class="theme-section-muted text-xs">
            This draft stays in this tab. Refreshing or closing it loses unsubmitted work.
          </p>
          <p
            v-if="catalog === 'error'"
            class="theme-alert-danger text-sm"
          >
            Heroes could not be loaded. Library-only imports are still available.
            <button
              type="button"
              class="btn-secondary mt-2"
              :disabled="running"
              @click="loadHeroes"
            >
              Retry hero loading
            </button>
          </p>
          <p
            v-if="unresolved"
            class="theme-alert-danger text-sm"
          >
            Resolve the unconfirmed rows before leaving or starting another batch.
          </p>
        </div>
        <template #footer>
          <button
            class="btn-primary w-full"
            type="button"
            :disabled="!canSubmit"
            @click="submit"
          >
            {{ running ? 'Importing…' : 'Import prepared rows' }}
          </button>
          <p
            v-if="pending.length && !canSubmit && !running && !unresolved"
            class="theme-section-muted mt-2 text-xs"
          >
            Review the highlighted rows before importing.
          </p>
        </template>
      </AppStickyAside>
    </template>
    <div
      @dragover.prevent
      @drop.prevent="dropFiles"
    >
      <div class="theme-divider flex flex-wrap items-center justify-between gap-3 border-b pb-5">
        <div>
          <h2 class="theme-section-title text-lg font-semibold">
            Images
          </h2>
          <p class="theme-section-muted text-sm">
            Drop images here, or choose files. PNG, JPG, WebP, BMP, TIFF.
          </p>
        </div>
        <button
          class="btn-secondary inline-flex items-center gap-2"
          type="button"
          :disabled="running"
          @click="fileInput?.click()"
        >
          <ImagePlus class="h-4 w-4" /> Choose images
        </button>
        <input
          ref="fileInput"
          type="file"
          multiple
          class="hidden"
          accept=".png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
          aria-label="Card-back images"
          @change="chooseFiles"
        >
      </div>
      <div
        v-if="catalog === 'loading' && rows.length === 0"
        aria-label="Loading import"
        class="space-y-5 py-5"
      >
        <div
          v-for="i in 3"
          :key="i"
          class="theme-muted-panel h-32 animate-pulse rounded"
        />
      </div>
      <p
        v-else-if="rows.length === 0"
        class="theme-empty-state py-16 text-center"
      >
        Choose images to start preparing your card backs.
      </p>
      <CardBackImportRowView
        v-for="row in rows"
        :key="row.id"
        :row="row"
        :heroes="heroes"
        :heroes-ready="catalog === 'ready'"
        :disabled="running"
        :disabled-hero-ids="disabledHeroes(row)"
        :error="isEditableRow(row) ? rowError(row) : ''"
        @remove="removeRow(row)"
        @label="row.label = $event"
        @hero="selectHero(row, $event)"
        @confirm="confirmReplacement(row, $event)"
        @retry="retry(row)"
      />
    </div>
  </AppPageLayout>
  <ConfirmModal
    :open="leavePrompt !== null"
    title="Discard this import draft?"
    message="Unsubmitted images, labels, and hero selections will be lost. Completed imports remain in the library."
    confirm-label="Discard draft"
    @confirm="resolveLeave(true)"
    @cancel="resolveLeave(false)"
  />
</template>

<script setup lang="ts">
import { computed, onMounted, onScopeDispose, ref } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import { useEventListener } from '@vueuse/core';
import { ImagePlus } from 'lucide-vue-next';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import AppStickyAside from '@/shared/components/app/AppStickyAside.vue';
import ConfirmModal from '@/shared/components/modals/ConfirmModal.vue';
import { APP_SECTION_ICONS } from '@/shared/components/app/appSectionIcons';
import CardBackImportRowView from '@/features/admin/components/CardBackImportRow.vue';
import { isEditableRow, useCardBackImport, type CardBackImportRow } from '@/features/admin/composables/useCardBackImport';

const {
  rows, heroes, catalog, running, pending, unresolved, hasUnsaved, usedHeroIds,
  loadHeroes, addFiles, removeRow, selectHero, rowError, canSubmit, submit, retry,
} = useCardBackImport();
const fileInput = ref<HTMLInputElement | null>(null);
const leavePrompt = ref<((value: boolean) => void) | null>(null);
const libraryCount = computed(() => pending.value.filter((row) => row.selection.kind === 'none').length);
const heroCount = computed(() => pending.value.filter((row) => row.selection.kind === 'selected').length);
const replacementCount = computed(() => pending.value.filter((row) => row.selection.kind === 'selected'
  && row.selection.hero.card_back_override_id !== null).length);
const completedCount = computed(() => rows.value.filter((row) => row.state.kind === 'succeeded').length);
const disabledHeroes = (row: CardBackImportRow): string[] => usedHeroIds.value.filter((id) =>
  row.selection.kind !== 'selected' || row.selection.hero.id !== id);
const confirmReplacement = (row: CardBackImportRow, confirmed: boolean): void => {
  if (!running.value && isEditableRow(row) && row.selection.kind === 'selected') row.selection.replacementConfirmed = confirmed;
};
const chooseFiles = (event: Event): void => {
  const input = event.target as HTMLInputElement;
  addFiles(Array.from(input.files ?? []));
  input.value = '';
};
const dropFiles = (event: DragEvent): void => addFiles(Array.from(event.dataTransfer?.files ?? []));
const resolveLeave = (leave: boolean): void => {
  leavePrompt.value?.(leave);
  leavePrompt.value = null;
};
onBeforeRouteLeave(() => {
  if (running.value || unresolved.value) return false;
  if (!hasUnsaved.value) return true;
  if (leavePrompt.value) return false;
  return new Promise<boolean>((resolve) => { leavePrompt.value = resolve; });
});
useEventListener(window, 'beforeunload', (event) => {
  if (hasUnsaved.value || running.value) {
    event.preventDefault();
    event.returnValue = '';
  }
});
onScopeDispose(() => resolveLeave(false));
onMounted(loadHeroes);
</script>
