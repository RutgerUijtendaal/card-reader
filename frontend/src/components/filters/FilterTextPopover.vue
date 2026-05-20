<template>
  <div class="relative inline-block">
    <button
      ref="triggerRef"
      type="button"
      class="filter-chip"
      :class="
        hasValue
          ? 'theme-choice-chip-active'
          : 'theme-choice-chip'
      "
      @click="toggle"
    >
      {{ label }} <span v-if="hasValue">(active)</span>
    </button>

    <Teleport to="body">
      <div
        v-if="isOpen"
        ref="panelRef"
        class="theme-popover z-50 w-64"
        :style="{ position: 'fixed', left: `${x}px`, top: `${y}px` }"
      >
        <label class="theme-section-muted grid gap-2 text-xs font-medium">
          {{ label }}
          <input
            :value="modelValue"
            class="input-base"
            :placeholder="placeholder"
            :type="inputType"
            :step="step"
            :min="min"
            :max="max"
            @input="onInput"
            @keyup.enter="close"
          >
        </label>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useFloatingPopover } from '@/composables/useFloatingPopover';

const props = withDefaults(
  defineProps<{
    label: string;
    modelValue: string;
    placeholder?: string;
    inputType?: 'text' | 'number';
    step?: string;
    min?: string;
    max?: string;
  }>(),
  {
    placeholder: '',
    inputType: 'text',
    step: undefined,
    min: undefined,
    max: undefined,
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const { isOpen, triggerRef, panelRef, x, y, toggle, close } = useFloatingPopover();

const hasValue = computed(() => props.modelValue.trim().length > 0);

const onInput = (event: Event): void => {
  const target = event.target as HTMLInputElement;
  emit('update:modelValue', target.value);
};
</script>

<style scoped>
.filter-chip {
  @apply rounded-md border px-3 py-1.5 text-xs font-semibold transition;
}
</style>
