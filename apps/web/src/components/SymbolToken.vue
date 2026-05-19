<template>
  <img
    v-if="assetUrl"
    :src="toAbsoluteApiUrl(assetUrl)"
    :alt="label"
    class="object-contain"
  >
  <span
    v-else
    class="inline-flex items-center justify-center"
  >{{ fallbackLabel }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';

const props = withDefaults(
  defineProps<{
    assetUrl?: string | null;
    label: string;
    textToken?: string | null;
  }>(),
  {
    assetUrl: null,
    textToken: '',
  },
);

const fallbackLabel = computed(() => props.textToken?.trim() || props.label);

</script>
