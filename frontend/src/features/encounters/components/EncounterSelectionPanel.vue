<template>
  <AppStickyAside
    :side="side"
    :footer-visible="!!editor.boss.value"
  >
    <div class="space-y-5">
      <div class="space-y-1">
        <h3 class="theme-section-title text-lg font-semibold">
          Encounter Setup
        </h3>
        <p class="theme-section-muted text-sm">
          Choose or replace the boss for this Encounter.
        </p>
      </div>
      <CardBuilderSelection
        :card="editor.boss.value"
        label="Selected Boss"
      >
        <p
          v-if="editor.form.boss_group_id"
          class="theme-section-muted text-sm"
        >
          Includes all linked boss cards on export.
        </p>
      </CardBuilderSelection>
      <label class="field-label"><span>Name <span class="theme-error-text">*</span></span><input
        :value="editor.form.name"
        class="input-base"
        placeholder="Encounter name"
        :disabled="editor.locked.value"
        @input="editor.setDetails({ name: ($event.target as HTMLInputElement).value })"
      ></label>
    </div>
    <template #footer>
      <button
        class="btn-secondary w-full justify-center"
        type="button"
        :disabled="editor.locked.value"
        @click="editor.selectBoss(null)"
      >
        Clear Boss
      </button>
    </template>
  </AppStickyAside>
</template>
<script setup lang="ts">
import AppStickyAside from '@/shared/components/app/AppStickyAside.vue';
import CardBuilderSelection from '@/domain/cards/components/CardBuilderSelection.vue';
import type { useEncounterEditor } from '../composables/useEncounterEditor';
withDefaults(
  defineProps<{ editor: ReturnType<typeof useEncounterEditor>; side?: 'left' | 'right' }>(),
  { side: 'right' },
);
</script>
