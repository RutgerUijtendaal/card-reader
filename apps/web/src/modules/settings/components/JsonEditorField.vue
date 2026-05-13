<template>
  <div class="space-y-2">
    <div class="flex items-center justify-between gap-3">
      <div class="text-sm font-medium text-slate-700">
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

    <div class="relative">
      <textarea
        :value="modelValue"
        class="json-textarea w-full rounded-lg border border-slate-300 bg-white px-3 py-3 pr-11 font-mono text-[13px] text-slate-900 outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-200"
        :style="{ minHeight }"
        spellcheck="false"
        @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
      />

      <div class="absolute right-4 top-3 group">
        <div
          class="inline-flex h-6 w-6 items-center justify-center rounded-full border bg-white shadow-sm"
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

        <div class="pointer-events-none absolute right-0 top-8 z-10 hidden w-64 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600 shadow-lg group-hover:block">
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
      class="flex items-center gap-2 text-xs font-normal text-slate-500"
    >
      <span>{{ hint }}</span>
      <button
        v-if="exampleJson"
        class="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px] font-medium text-slate-600 transition hover:border-sky-300 hover:text-sky-700"
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
        class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
        @click.self="showExample = false"
      >
        <div class="w-full max-w-2xl rounded-xl border border-slate-200 bg-white p-5 shadow-xl">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h3 class="text-base font-semibold text-slate-900">
                {{ exampleTitle || 'Example JSON' }}
              </h3>
              <p class="mt-1 text-sm text-slate-600">
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

          <pre class="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700"><code>{{ exampleJson }}</code></pre>
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
    exampleTitle?: string;
    exampleJson?: string;
  }>(),
  {
    hint: '',
    minHeight: '15rem',
    exampleTitle: '',
    exampleJson: '',
  },
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const showExample = ref(false);

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
</style>
