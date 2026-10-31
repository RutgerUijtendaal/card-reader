<template>
  <section class="space-y-5">
    <div class="space-y-1">
      <h2 class="theme-section-title text-xl font-semibold">
        {{ kind }} details
      </h2>
      <p class="theme-section-muted text-sm">
        {{ description }}
      </p>
    </div>
    <label
      :for="`${fieldPrefix}-name-field`"
      class="field-label"
    ><span>Name <span class="theme-error-text">*</span></span><input
      :id="`${fieldPrefix}-name-field`"
      ref="nameInput"
      v-model="name"
      class="input-base"
      :placeholder="`${kind} name`"
      required
    ></label>
    <div class="field-label">
      <span>Summary</span><CardMarkupEditor
        v-model="summary"
        :label="`${kind} summary`"
        :preferred-card-pool="pool"
        :textarea-id="`${fieldPrefix}-summary-field`"
        min-height-class="min-h-20"
        :placeholder="`A short summary shown in ${kind.toLowerCase()} lists`"
      />
    </div>
    <div class="field-label">
      <span>Long description</span><CardMarkupEditor
        v-model="longDescription"
        :label="`${kind} long description`"
        :preferred-card-pool="pool"
        :textarea-id="`${fieldPrefix}-long-description-field`"
        min-height-class="min-h-64"
        placeholder="Optional notes, strategy, or other information"
      />
    </div>
  </section>
</template>
<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';
import CardMarkupEditor from '@/domain/cards/components/CardMarkupEditor.vue';
import type { CardPool } from '@/domain/cards/cardPools';
const props = defineProps<{
  kind: string;
  description: string;
  fieldPrefix: string;
  pool: CardPool;
  focusRequest?: number;
}>();
const name = defineModel<string>('name', { required: true });
const summary = defineModel<string>('summary', { required: true });
const longDescription = defineModel<string>('longDescription', { required: true });
const nameInput = ref<HTMLInputElement | null>(null);
watch(
  () => props.focusRequest,
  async () => {
    await nextTick();
    nameInput.value?.focus({ preventScroll: true });
  },
);
</script>
