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
import { api, DEFAULT_API_BASE_URL } from '@/api/client';

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

const toAbsoluteApiUrl = (urlPath: string): string => {
  const base = api.defaults.baseURL ?? DEFAULT_API_BASE_URL;
  if (urlPath.startsWith('http://') || urlPath.startsWith('https://')) {
    return urlPath;
  }
  return `${base.replace(/\/$/, '')}/${urlPath.replace(/^\//, '')}`;
};
</script>
