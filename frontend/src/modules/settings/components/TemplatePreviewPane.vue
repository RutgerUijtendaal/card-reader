<template>
  <section class="theme-card-frame-muted flex min-h-0 flex-col rounded-2xl p-3">
    <div class="shrink-0 space-y-2">
      <div class="flex items-center justify-between gap-3">
        <h4 class="theme-section-title text-sm font-semibold">
          Region Preview
        </h4>
        <span
          v-if="selectedPreviewCard"
          class="theme-section-muted truncate text-xs"
        >
          {{ selectedPreviewCard.template_id }}
        </span>
      </div>

      <TemplatePreviewCardPicker
        :cards="previewCards"
        :loading="previewLoading"
        :scope="previewScope"
        :search-query="previewSearchQuery"
        :selected-card="selectedPreviewCard"
        :template-scope-available="templateScopeAvailable"
        @update:scope="emit('update:scope', $event)"
        @update:search-query="emit('update:searchQuery', $event)"
        @select="emit('selectCard', $event)"
      />
    </div>

    <div
      v-if="previewWarning"
      class="theme-info-box mt-3 rounded-xl px-3 py-2 text-sm"
    >
      {{ previewWarning }}
    </div>

    <div class="mt-3 flex min-h-0 flex-1 flex-col">
      <div
        v-if="selectedPreviewCard?.image_url"
        class="theme-card-frame min-h-[28rem] flex-1 overflow-hidden rounded-[1.5rem]"
      >
        <div
          ref="stageRef"
          class="flex h-full w-full items-start justify-center p-3"
        >
          <div
            class="relative overflow-hidden rounded-[1.2rem]"
            :style="previewCardStyle"
          >
            <img
              :src="toAbsoluteApiUrl(selectedPreviewCard.image_url)"
              :alt="selectedPreviewCard.name"
              class="block h-full w-full"
              @load="handleImageLoad"
            >
            <TemplateRegionOverlay
              v-if="previewRegions.length > 0"
              :regions="previewRegions"
            />
          </div>
        </div>
      </div>

      <div
        v-else
        class="theme-card-frame theme-section-muted flex min-h-[28rem] flex-1 items-center justify-center rounded-2xl px-6 text-center text-sm"
      >
        Choose a preview card to visualize the template regions.
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useElementSize } from '@vueuse/core';
import { computed, ref, watch } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';
import TemplatePreviewCardPicker from '@/modules/settings/components/TemplatePreviewCardPicker.vue';
import TemplateRegionOverlay from '@/modules/settings/components/TemplateRegionOverlay.vue';
import type {
  TemplatePreviewCardOption,
  TemplatePreviewRenderRegion,
  TemplatePreviewScope,
} from '@/modules/settings/types';

const props = defineProps<{
  previewCards: TemplatePreviewCardOption[];
  previewLoading: boolean;
  previewRegions: TemplatePreviewRenderRegion[];
  previewScope: TemplatePreviewScope;
  previewSearchQuery: string;
  previewWarning: string | null;
  selectedPreviewCard: TemplatePreviewCardOption | null;
  templateScopeAvailable: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:scope', value: TemplatePreviewScope): void;
  (e: 'update:searchQuery', value: string): void;
  (e: 'selectCard', value: TemplatePreviewCardOption): void;
}>();

const stageRef = ref<HTMLElement | null>(null);
const naturalWidth = ref(0);
const naturalHeight = ref(0);
const { width: stageWidth, height: stageHeight } = useElementSize(stageRef);

const previewCardStyle = computed<Record<string, string>>(() => {
  if (!naturalWidth.value || !naturalHeight.value || !stageWidth.value || !stageHeight.value) {
    return {
      width: '100%',
      height: 'auto',
    };
  }

  const ratio = naturalWidth.value / naturalHeight.value;
  let renderWidth = stageWidth.value;
  let renderHeight = renderWidth / ratio;

  if (renderHeight > stageHeight.value) {
    renderHeight = stageHeight.value;
    renderWidth = renderHeight * ratio;
  }

  return {
    width: `${Math.max(renderWidth, 0)}px`,
    height: `${Math.max(renderHeight, 0)}px`,
  };
});

const handleImageLoad = (event: Event): void => {
  const image = event.target as HTMLImageElement | null;
  if (!image) return;
  naturalWidth.value = image.naturalWidth;
  naturalHeight.value = image.naturalHeight;
};

watch(
  () => props.selectedPreviewCard?.image_url,
  () => {
    naturalWidth.value = 0;
    naturalHeight.value = 0;
  },
);
</script>
