<template>
  <AppModal
    :open="open"
    :aria-labelledby="titleId"
    panel-class="theme-popover w-full max-w-lg shadow-xl"
    close-disabled
  >
    <h3
      :id="titleId"
      class="theme-section-title text-base font-semibold"
    >
      {{ copy.title }}
    </h3>
    <p class="theme-section-muted mt-2 text-sm">
      {{ busy ? 'Finish confirming the current Create request before resolving this conflict.' : copy.message }}
    </p>
    <div class="mt-5 flex flex-wrap justify-end gap-2">
      <button
        class="btn-secondary"
        type="button"
        :disabled="busy"
        @click="emit('useStored')"
      >
        {{ copy.storedLabel }}
      </button>
      <button
        class="btn-primary"
        type="button"
        :disabled="busy"
        @click="emit('keepLocal')"
      >
        {{ copy.localLabel }}
      </button>
    </div>
  </AppModal>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue';
import AppModal from '@/shared/components/modals/AppModal.vue';
import type { DeckEditorDraftConflict } from '@/features/decks/composables/useDeckEditorLocalDraft';

const props = defineProps<{
  open: boolean;
  kind?: DeckEditorDraftConflict['kind'];
  busy?: boolean;
}>();

const emit = defineEmits<{
  (event: 'useStored'): void;
  (event: 'keepLocal'): void;
}>();

const titleId = `deck-draft-conflict-title-${useId()}`;
const copy = computed(() => {
  if (props.kind === 'created-elsewhere') {
    return {
      title: 'This draft was created in another tab',
      message: 'Open the created deck, or keep this tab as a separate unpublished draft.',
      storedLabel: 'Open Created Deck',
      localLabel: 'Keep as New Draft',
    };
  }
  if (props.kind === 'remote-deletion') {
    return {
      title: 'This draft changed in another tab',
      message: 'The stored draft was removed. Discard this tab, or save its current contents as the draft.',
      storedLabel: 'Discard This Tab',
      localLabel: 'Keep This Draft',
    };
  }
  return {
    title: 'Another tab changed this draft',
    message: 'Load the stored version, or replace it with the current contents of this tab.',
    storedLabel: 'Load Stored Draft',
    localLabel: 'Keep This Draft',
  };
});
</script>
