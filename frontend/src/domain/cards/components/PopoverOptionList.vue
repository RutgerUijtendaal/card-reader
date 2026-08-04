<template>
  <div :class="appearance === 'list' ? 'space-y-3' : 'space-y-2'">
    <div
      v-if="title || description"
      :class="appearance === 'list' ? 'space-y-1' : 'pb-1'"
    >
      <p
        v-if="title"
        class="theme-section-title text-sm font-semibold"
      >
        {{ title }}
      </p>
      <p
        v-if="description"
        class="theme-section-muted text-xs"
      >
        {{ description }}
      </p>
    </div>

    <div
      v-if="appearance === 'list'"
      class="theme-panel-shell overflow-hidden"
    >
      <button
        v-if="defaultOption"
        type="button"
        class="w-full px-3 py-3 text-left transition"
        :class="!selectionActive ? 'theme-selected-surface' : 'hover:bg-white/5'"
        @click="$emit('reset')"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="theme-section-title text-sm font-semibold">
              {{ defaultOption.label }}
            </p>
            <p
              v-if="defaultOption.description"
              class="theme-section-muted mt-1 text-xs"
            >
              {{ defaultOption.description }}
            </p>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <kbd
              v-if="defaultOption.hotkey"
              class="theme-card-frame-muted theme-section-muted rounded px-1.5 py-0.5 text-[0.625rem] font-semibold leading-none"
            >
              {{ defaultOption.hotkey }}
            </kbd>
            <Check
              v-if="!selectionActive"
              class="h-4 w-4"
            />
          </div>
        </div>
      </button>

      <div
        v-for="(option, index) in options"
        :key="option.value"
        :class="index > 0 || defaultOption ? 'theme-divider border-t' : ''"
      >
        <button
          type="button"
          class="w-full px-3 py-3 text-left transition"
          :class="selectionActive && selectedValue === option.value ? 'theme-selected-surface' : 'hover:bg-white/5'"
          @click="$emit('select', option.value)"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="theme-section-title text-sm font-semibold">
                {{ option.label }}
              </p>
              <p
                v-if="option.description"
                class="theme-section-muted mt-1 text-xs"
              >
                {{ option.description }}
              </p>
            </div>
            <div class="flex shrink-0 items-center gap-2">
              <kbd
                v-if="option.hotkey"
                class="theme-card-frame-muted theme-section-muted rounded px-1.5 py-0.5 text-[0.625rem] font-semibold leading-none"
              >
                {{ option.hotkey }}
              </kbd>
              <Check
                v-if="selectionActive && selectedValue === option.value"
                class="h-4 w-4"
              />
            </div>
          </div>
        </button>
      </div>
    </div>

    <template v-else>
      <button
        v-if="defaultOption"
        type="button"
        class="theme-card-frame w-full rounded-xl px-3 py-3 text-left transition hover:-translate-y-0.5"
        :class="!selectionActive ? 'theme-selected-surface-strong' : ''"
        @click="$emit('reset')"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="theme-section-title text-sm font-semibold">
              {{ defaultOption.label }}
            </p>
            <p
              v-if="defaultOption.description"
              class="theme-section-muted mt-1 text-xs"
            >
              {{ defaultOption.description }}
            </p>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <kbd
              v-if="defaultOption.hotkey"
              class="theme-card-frame-muted theme-section-muted rounded px-1.5 py-0.5 text-[0.625rem] font-semibold leading-none"
            >
              {{ defaultOption.hotkey }}
            </kbd>
            <Check
              v-if="!selectionActive"
              class="h-4 w-4"
            />
          </div>
        </div>
      </button>

      <button
        v-for="option in options"
        :key="option.value"
        type="button"
        class="theme-card-frame w-full rounded-xl px-3 py-3 text-left transition hover:-translate-y-0.5"
        :class="selectionActive && selectedValue === option.value ? 'theme-selected-surface-strong' : ''"
        @click="$emit('select', option.value)"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="theme-section-title text-sm font-semibold">
              {{ option.label }}
            </p>
            <p
              v-if="option.description"
              class="theme-section-muted mt-1 text-xs"
            >
              {{ option.description }}
            </p>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <kbd
              v-if="option.hotkey"
              class="theme-card-frame-muted theme-section-muted rounded px-1.5 py-0.5 text-[0.625rem] font-semibold leading-none"
            >
              {{ option.hotkey }}
            </kbd>
            <Check
              v-if="selectionActive && selectedValue === option.value"
              class="h-4 w-4"
            />
          </div>
        </div>
      </button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { Check } from 'lucide-vue-next';

export type PopoverOptionItem = {
  value: string;
  label: string;
  description?: string;
  hotkey?: string;
};

defineProps<{
  title?: string;
  description?: string;
  options: PopoverOptionItem[];
  selectedValue: string;
  selectionActive: boolean;
  appearance?: 'cards' | 'list';
  defaultOption?: {
    label: string;
    description?: string;
    hotkey?: string;
  } | null;
}>();

defineEmits<{
  (e: 'select', value: string): void;
  (e: 'reset'): void;
}>();
</script>
