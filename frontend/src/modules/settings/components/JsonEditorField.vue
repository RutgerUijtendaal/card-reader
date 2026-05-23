<template>
  <div
    class="space-y-2"
    :class="{ 'flex h-full min-h-0 flex-col': fillHeight }"
  >
    <div class="flex items-center justify-between gap-3">
      <div class="theme-section-title text-sm font-medium">
        {{ label }}
      </div>
      <button
        class="btn-secondary px-3 py-1.5 text-xs"
        type="button"
        @click="formatValue"
      >
        Format
      </button>
    </div>

    <div
      class="relative"
      :class="{ 'flex min-h-0 flex-1 flex-col': fillHeight }"
    >
      <textarea
        :value="modelValue"
        class="json-textarea input-base app-scrollbar w-full px-3 py-3 pr-11 font-mono text-[13px]"
        :class="{ 'min-h-0 flex-1': fillHeight }"
        :style="textareaStyle"
        spellcheck="false"
        @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
      />

      <div class="absolute right-4 top-3 group">
        <div
          class="theme-card-frame-muted inline-flex h-6 w-6 items-center justify-center rounded-full shadow-sm"
          :class="
            parseError
              ? 'border-rose-200 text-rose-600'
              : 'border-emerald-200 text-emerald-600'
          "
        >
          <CircleAlert
            v-if="parseError"
            class="h-3.5 w-3.5"
          />
          <CircleCheck
            v-else
            class="h-3.5 w-3.5"
          />
        </div>

        <div class="theme-popover pointer-events-none absolute right-0 top-8 z-10 hidden w-64 px-3 py-2 text-xs shadow-lg group-hover:block">
          <span
            class="font-semibold"
            :class="parseError ? 'text-rose-700' : 'text-emerald-700'"
          >
            {{ parseError ? 'Invalid JSON' : 'Valid JSON' }}
          </span>
          <p
            v-if="parseError"
            class="mt-1 text-rose-600"
          >
            {{ parseError }}
          </p>
        </div>
      </div>
    </div>

    <p
      v-if="hint"
      class="theme-section-muted flex items-center gap-2 text-xs font-normal"
    >
      <span>{{ hint }}</span>
      <button
        v-if="exampleJson"
        class="btn-secondary inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium"
        type="button"
        @click="showExample = true"
      >
        <CircleHelp class="h-3.5 w-3.5" />
        <span>Example</span>
      </button>
    </p>

    <Teleport to="body">
      <div
        v-if="showExample"
        class="theme-overlay fixed inset-0 z-50 flex items-center justify-center p-4"
        @click.self="showExample = false"
      >
        <div class="theme-popover flex max-h-[calc(100vh-2rem)] w-full max-w-2xl flex-col overflow-hidden shadow-xl">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h3 class="theme-section-title text-base font-semibold">
                {{ exampleTitle || 'Example JSON' }}
              </h3>
              <p class="theme-section-muted mt-1 text-sm">
                Reference example for this field.
              </p>
            </div>
            <button
              class="btn-secondary px-3 py-1.5 text-xs"
              type="button"
              @click="showExample = false"
            >
              Close
            </button>
          </div>

          <pre class="theme-card-frame-muted theme-section-title app-scrollbar mt-4 min-h-0 flex-1 overflow-auto rounded-lg p-4 text-xs"><code>{{ exampleJson }}</code></pre>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { CircleAlert, CircleCheck, CircleHelp } from 'lucide-vue-next';
import { toast } from 'vue-sonner';

const props = withDefaults(
  defineProps<{
    modelValue: string;
    label: string;
    hint?: string;
    minHeight?: string;
    fillHeight?: boolean;
    exampleTitle?: string;
    exampleJson?: string;
  }>(),
  {
    hint: '',
    minHeight: '15rem',
    fillHeight: false,
    exampleTitle: '',
    exampleJson: '',
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const showExample = ref(false);

const textareaStyle = computed<Record<string, string>>(() => {
  if (props.fillHeight) {
    return { height: '100%', minHeight: props.minHeight };
  }

  return { height: 'auto', minHeight: props.minHeight };
});

const parseError = computed(() => {
  const trimmed = props.modelValue.trim();
  if (!trimmed) return null;

  try {
    JSON.parse(trimmed);
    return null;
  } catch (error) {
    if (error instanceof Error) {
      return error.message;
    }

    return 'Unable to parse JSON.';
  }
});

const formatValue = (): void => {
  const trimmed = props.modelValue.trim();
  if (!trimmed) {
    toast.error('Nothing to format.');
    return;
  }

  try {
    const formatted = JSON.stringify(JSON.parse(trimmed), null, 2);
    emit('update:modelValue', formatted);
    toast.success('JSON formatted.');
  } catch (error) {
    const message = error instanceof Error ? error.message : 'JSON is invalid.';
    toast.error(`Cannot format JSON: ${message}`);
  }
};
</script>

<style scoped>
.json-textarea {
  resize: vertical;
  line-height: 1.5;
  tab-size: 2;
}

.json-textarea.min-h-0.flex-1 {
  resize: none;
}
</style>
