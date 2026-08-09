<template>
  <fieldset
    class="theme-divider border-t pt-3"
    :aria-describedby="description ? descriptionId : undefined"
  >
    <legend class="theme-section-title pr-2 text-base font-semibold">
      {{ title }}
    </legend>
    <p
      v-if="description"
      :id="descriptionId"
      class="theme-section-muted mt-1 text-sm"
    >
      {{ description }}
    </p>
    <div
      class="app-form-section-content"
      :class="description ? 'mt-4' : 'mt-3'"
    >
      <slot />
    </div>
  </fieldset>
</template>

<script setup lang="ts">
import { useId } from 'vue';

defineProps<{
  title: string;
  description?: string;
}>();

const descriptionId = `app-form-section-description-${useId()}`;
</script>
