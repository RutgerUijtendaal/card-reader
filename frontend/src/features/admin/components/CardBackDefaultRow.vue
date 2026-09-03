<template>
  <article class="theme-divider grid gap-3 border-b py-3 last:border-b-0 sm:grid-cols-[minmax(8rem,0.45fr)_minmax(14rem,1fr)_7rem] sm:items-center">
    <h4 class="theme-section-title text-sm font-semibold">
      {{ label }}
    </h4>

    <AppSelect
      :model-value="modelValue"
      :options="options"
      :placeholder="placeholder"
      :placeholder-disabled="false"
      :disabled="disabled"
      wrapper-class="w-full"
      :aria-label="selectLabel"
      @update:model-value="handleUpdate"
    />

    <div class="flex min-h-10 items-center gap-2 sm:justify-end">
      <template v-if="selectedAsset">
        <div class="theme-card-frame theme-card-image-well flex h-10 w-7 shrink-0 items-center justify-center overflow-hidden rounded">
          <img
            v-if="selectedAsset.image_url"
            class="h-full w-full object-cover"
            :src="toAbsoluteApiUrl(selectedAsset.image_url)"
            :alt="`${selectedAsset.label} preview`"
          >
          <ImageOff
            v-else
            class="theme-section-muted h-4 w-4"
            aria-label="Image unavailable"
          />
        </div>
        <span class="theme-pill theme-pill-success px-2 py-0.5 text-xs">
          Set
        </span>
      </template>
      <span
        v-else
        class="theme-section-muted text-xs"
      >
        Not set
      </span>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { ImageOff } from 'lucide-vue-next';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import AppSelect from '@/shared/components/app/AppSelect.vue';
import type { CardBackRecord } from '@/domain/card-backs/types';

const props = withDefaults(defineProps<{
  modelValue: string | null;
  label: string;
  placeholder: string;
  selectLabel: string;
  assets: CardBackRecord[];
  disabled?: boolean;
}>(), {
  disabled: false,
});

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | null): void;
}>();

const options = computed(() => props.assets.map((asset) => ({
  value: asset.id,
  label: `${asset.label}${asset.is_usable ? '' : ' (missing image)'}`,
  disabled: !asset.is_usable,
})));
const selectedAsset = computed(() =>
  props.assets.find((asset) => asset.id === props.modelValue) ?? null,
);

const handleUpdate = (value: string | number | null): void => {
  emit('update:modelValue', value === null ? null : String(value));
};
</script>
