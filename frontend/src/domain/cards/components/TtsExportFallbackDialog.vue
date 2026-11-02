<template>
  <AppModal
    :open="fallback !== null"
    aria-labelledby="tts-export-fallback-title"
    aria-describedby="tts-export-fallback-description"
    panel-class="theme-popover w-full max-w-lg p-5"
    @close="dismiss"
  >
    <div class="space-y-4">
      <div class="space-y-1">
        <h2
          id="tts-export-fallback-title"
          class="theme-section-title theme-display text-xl"
        >
          Copy the TTS import code
        </h2>
        <p
          id="tts-export-fallback-description"
          class="theme-section-muted text-sm"
        >
          Your browser blocked automatic copying. Select the code below and copy it into Tabletop
          Simulator. {{ fallback?.summary }}
        </p>
      </div>
      <label class="field-label">
        TTS import code
        <textarea
          ref="textareaRef"
          :value="fallback?.payload ?? ''"
          readonly
          class="input-base h-28 font-mono text-xs"
          data-testid="tts-export-fallback-code"
          @focus="($event.target as HTMLTextAreaElement).select()"
        />
      </label>
      <div class="flex justify-end gap-2">
        <button
          class="btn-secondary"
          type="button"
          @click="dismiss"
        >
          Close
        </button>
        <button
          class="btn-primary"
          type="button"
          @click="copyAgain"
        >
          Copy code
        </button>
      </div>
    </div>
  </AppModal>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import AppModal from '@/shared/components/modals/AppModal.vue';
import { useTtsExportFallback } from '@/domain/cards/composables/useTtsExportFallback';

const { fallback, dismiss } = useTtsExportFallback();
const textareaRef = ref<HTMLTextAreaElement | null>(null);

watch(fallback, async (value) => {
  if (!value) return;
  await nextTick();
  textareaRef.value?.focus();
  textareaRef.value?.select();
});

const copyAgain = async (): Promise<void> => {
  const payload = fallback.value?.payload;
  if (!payload) return;
  try {
    await navigator.clipboard.writeText(payload);
    toast.success('TTS import code copied to clipboard');
    dismiss();
  } catch {
    textareaRef.value?.select();
  }
};
</script>
