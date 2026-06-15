<template>
  <div class="relative">
    <Search class="theme-section-muted pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" />
    <input
      ref="inputRef"
      :value="modelValue"
      class="input-base w-full pl-10"
      :class="[hasTrailing ? 'pr-12' : 'pr-3', inputClass]"
      :placeholder="placeholder"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    >
    <div
      v-if="hasTrailing"
      class="pointer-events-none absolute inset-y-0 right-3 flex items-center gap-1.5"
      aria-hidden="true"
    >
      <slot name="trailing" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useSlots } from 'vue';
import { Search } from 'lucide-vue-next';

withDefaults(
  defineProps<{
    modelValue: string;
    placeholder?: string;
    inputClass?: string;
  }>(),
  {
    placeholder: undefined,
    inputClass: '',
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const slots = useSlots();
const inputRef = ref<HTMLInputElement | null>(null);
const inputElement = computed(() => inputRef.value);
const hasTrailing = computed(() => Boolean(slots.trailing));

defineExpose({
  inputElement,
});
</script>
