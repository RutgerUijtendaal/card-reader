<template>
  <div
    class="app-select"
    :class="wrapperClass"
  >
    <select
      v-bind="$attrs"
      :value="normalizedValue"
      class="input-base app-select-input"
      :class="selectClass"
      @change="handleChange"
    >
      <option
        v-if="placeholder !== undefined"
        :value="placeholderValue"
        :disabled="placeholderDisabled"
      >
        {{ placeholder }}
      </option>
      <option
        v-for="option in options"
        :key="String(option.value)"
        :value="String(option.value)"
        :disabled="option.disabled"
      >
        {{ option.label }}
      </option>
    </select>
    <span
      class="app-select-chevron"
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 20 20"
        fill="none"
        class="h-4 w-4"
      >
        <path
          d="M5 7.5L10 12.5L15 7.5"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </span>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

type SelectValue = string | number;

type SelectOption = {
  value: SelectValue;
  label: string;
  disabled?: boolean;
};

const props = withDefaults(
  defineProps<{
    modelValue?: SelectValue | null;
    options: readonly SelectOption[];
    placeholder?: string;
    placeholderDisabled?: boolean;
    wrapperClass?: string;
    selectClass?: string;
  }>(),
  {
    modelValue: null,
    placeholder: undefined,
    placeholderDisabled: false,
    wrapperClass: '',
    selectClass: '',
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: SelectValue | null): void;
  (e: 'change', value: SelectValue | null): void;
}>();

const placeholderValue = '__placeholder__';
const normalizedValue =
  props.modelValue === null || props.modelValue === undefined ? placeholderValue : String(props.modelValue);

const handleChange = (event: Event): void => {
  const nextRawValue = (event.target as HTMLSelectElement).value;
  if (nextRawValue === placeholderValue) {
    emit('update:modelValue', null);
    emit('change', null);
    return;
  }

  const matchedOption = props.options.find((option) => String(option.value) === nextRawValue);
  const nextValue = matchedOption?.value ?? nextRawValue;
  emit('update:modelValue', nextValue);
  emit('change', nextValue);
};
</script>
