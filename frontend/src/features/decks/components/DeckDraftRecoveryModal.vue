<template>
  <AppModal
    :open="open"
    :aria-labelledby="titleId"
    :aria-describedby="descriptionId"
    panel-class="theme-popover w-full max-w-md p-5 shadow-xl"
    :close-on-overlay="false"
    :close-on-escape="false"
  >
    <div class="space-y-2">
      <h3
        :id="titleId"
        class="theme-section-title text-lg font-semibold"
      >
        Resume local deck draft?
      </h3>
      <p
        :id="descriptionId"
        class="theme-section-muted text-sm"
      >
        This browser has an unpublished deck draft. Resume where you left off or discard it and
        start a new deck.
      </p>
      <p
        v-if="savedAtLabel"
        class="theme-kicker text-xs"
      >
        Last updated {{ savedAtLabel }}
      </p>
    </div>

    <div class="mt-5 flex flex-wrap justify-end gap-2">
      <button
        class="btn-danger-secondary"
        type="button"
        @click="emit('discard')"
      >
        Discard Draft
      </button>
      <button
        class="btn-primary"
        type="button"
        @click="emit('resume')"
      >
        Resume Draft
      </button>
    </div>
  </AppModal>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue';
import AppModal from '@/shared/components/modals/AppModal.vue';

const props = defineProps<{
  open: boolean;
  savedAt?: string;
}>();

const emit = defineEmits<{
  discard: [];
  resume: [];
}>();

const titleId = `deck-draft-recovery-title-${useId()}`;
const descriptionId = `deck-draft-recovery-description-${useId()}`;
const savedAtLabel = computed(() => {
  if (!props.savedAt) {
    return '';
  }
  const timestamp = new Date(props.savedAt);
  return Number.isNaN(timestamp.getTime()) ? '' : timestamp.toLocaleString();
});
</script>
