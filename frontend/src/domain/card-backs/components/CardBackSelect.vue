<template>
  <div class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_5rem] sm:items-start">
    <div>
      <AppSelect
        :model-value="modelValue"
        :options="options"
        :placeholder="placeholderLabel"
        :placeholder-disabled="selectionKind === 'default'"
        :disabled="disabled"
        wrapper-class="w-full"
        :aria-label="ariaLabel"
        @update:model-value="handleUpdate"
      />
      <p
        v-if="error"
        class="theme-alert-danger mt-2 text-xs"
      >
        {{ error }}
      </p>
      <p
        v-else
        class="theme-section-muted mt-2 text-xs"
      >
        {{ selectionDescription }}
      </p>
    </div>
    <div class="theme-card-frame theme-card-image-well aspect-[63/88] overflow-hidden rounded-lg">
      <img
        v-if="effectiveAsset?.image_url"
        class="h-full w-full object-cover"
        :src="toAbsoluteApiUrl(effectiveAsset.image_url)"
        :alt="effectiveAsset.label"
      >
      <div
        v-else
        class="theme-section-muted flex h-full items-center justify-center p-2 text-center text-[0.65rem]"
      >
        {{ effectiveAsset ? 'Missing image' : 'Unavailable' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import AppSelect from '@/shared/components/app/AppSelect.vue';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import { CARD_POOL_OPTIONS, type CardPool } from '@/domain/cards/cardPools';
import type {
  CardBackDefaults,
  CardBackRecord,
  PublicCardBackRecord,
} from '@/domain/card-backs/types';

const props = withDefaults(defineProps<{
  modelValue: string | null;
  cardPool: CardPool;
  assets: CardBackRecord[];
  defaults: CardBackDefaults;
  disabled?: boolean;
  error?: string;
  ariaLabel?: string;
  selectionKind?: 'override' | 'default';
}>(), {
  disabled: false,
  error: '',
  ariaLabel: 'Card back override',
  selectionKind: 'override',
});

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | null): void;
}>();

const options = computed(() => props.assets.map((asset) => ({
  value: asset.id,
  label: `${asset.label}${asset.is_usable ? '' : ' (missing image)'}`,
  disabled: !asset.is_usable,
})));
const poolLabel = computed(() =>
  CARD_POOL_OPTIONS.find((option) => option.value === props.cardPool)?.label ?? props.cardPool,
);
const placeholderLabel = computed(() =>
  props.selectionKind === 'default'
    ? `Select ${poolLabel.value} default`
    : `Use ${poolLabel.value} default`,
);
const selectedAsset = computed<PublicCardBackRecord | null>(() =>
  props.assets.find((asset) => asset.id === props.modelValue) ?? null,
);
const effectiveAsset = computed(() => selectedAsset.value ?? props.defaults[props.cardPool]);
const selectionDescription = computed(() => {
  if (selectedAsset.value) {
    return props.selectionKind === 'default'
      ? `Selected ${poolLabel.value} default: ${selectedAsset.value.label}`
      : `Override: ${selectedAsset.value.label}`;
  }
  const inherited = props.defaults[props.cardPool];
  return inherited ? `Inherited ${poolLabel.value} default: ${inherited.label}` : `${poolLabel.value} has no default.`;
});

const handleUpdate = (value: string | number | null): void => {
  emit('update:modelValue', value === null ? null : String(value));
};
</script>
