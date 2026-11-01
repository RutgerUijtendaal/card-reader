<template>
  <div
    class="theme-toggle-shell"
    role="group"
    :aria-label="label"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="theme-toggle-option whitespace-nowrap"
      :class="{ 'theme-toggle-option-active': modelValue === option.value }"
      :aria-pressed="modelValue === option.value"
      :disabled="disabled"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<script setup lang="ts" generic="T extends string">
/** A compact single-choice switch for toolbar rows, such as Cards / Heroes or All / Official. */
withDefaults(
  defineProps<{
    label: string;
    options: readonly { value: T; label: string }[];
    modelValue: T;
    disabled?: boolean;
  }>(),
  { disabled: false },
);

const emit = defineEmits<{
  'update:modelValue': [value: T];
}>();
</script>
