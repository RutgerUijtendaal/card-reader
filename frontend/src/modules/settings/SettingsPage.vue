<template>
  <section class="flex w-full flex-col gap-6">
    <AppPageHeader
      :icon="SlidersHorizontal"
      title="Settings"
      subtitle="Configure default browsing and viewing preferences."
      title-tag="h2"
      title-class="text-xl"
    />

    <section class="page-card mx-auto w-full max-w-3xl space-y-6">
      <div class="space-y-1">
        <h3 class="theme-section-title text-base font-semibold">
          Card Browsing
        </h3>
        <p class="theme-section-muted text-sm">
          These defaults apply anywhere card lists use the shared local preferences.
        </p>
      </div>

      <div class="theme-divider space-y-3 border-t pt-5">
        <PopoverOptionList
          title="Default Card Sort"
          description="Used by card-browsing screens unless that screen has its own override selected."
          appearance="list"
          :options="cardSortMenuOptions"
          :selected-value="defaultSort"
          :selection-active="true"
          @select="handleDefaultSortSelect"
        />
      </div>

      <div class="theme-divider space-y-4 border-t pt-5">
        <PopoverOptionList
          title="Default Hover Preview"
          description="Choose the default card hover behavior for gallery and deck browsing views."
          appearance="list"
          :options="hoverModeMenuOptions"
          :selected-value="defaultHoverMode"
          :selection-active="true"
          @select="handleDefaultHoverModeSelect"
        />

        <section class="space-y-2">
          <div>
            <p class="theme-section-title text-sm font-semibold">
              Display
            </p>
            <p class="theme-section-muted text-sm">
              Control the default gallery layout and request size.
            </p>
          </div>

          <div class="theme-muted-panel space-y-0 p-0">
            <label class="flex items-start justify-between gap-4 px-4 py-3">
              <div class="min-w-0">
                <p class="theme-section-title text-sm font-semibold">
                  Card Groups
                </p>
                <p class="theme-section-muted mt-1 text-sm">
                  Show grouped cards as stacked gallery results when available.
                </p>
              </div>
              <input
                v-model="showCardGroups"
                type="checkbox"
                class="theme-checkbox mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300"
              >
            </label>

            <div class="theme-divider border-t px-4 py-3">
              <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
                <div class="min-w-0">
                  <p class="theme-section-title text-sm font-semibold">
                    Cards Per Page
                  </p>
                  <p class="theme-section-muted mt-1 text-sm">
                    Default gallery request size for card browsing.
                  </p>
                </div>
                <AppSelect
                  v-model="pageSize"
                  :options="cardPageSizeSelectOptions"
                  wrapper-class="w-full sm:ml-auto sm:w-[8rem] sm:shrink-0"
                />
              </div>
            </div>

            <div class="theme-divider border-t px-4 py-3">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <p class="theme-section-title text-sm font-semibold">
                    Card Size
                  </p>
                  <p class="theme-section-muted mt-1 text-sm">
                    Scale card thumbnails in gallery-style views.
                  </p>
                </div>
                <span class="theme-section-muted text-sm font-medium">
                  {{ percentLabel }}
                </span>
              </div>
              <input
                v-model="cardScale"
                type="range"
                min="0.8"
                max="1.2"
                step="0.05"
                class="theme-range mt-3 w-full"
              >
            </div>
          </div>
        </section>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { SlidersHorizontal } from 'lucide-vue-next';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import AppSelect from '@/components/app/AppSelect.vue';
import PopoverOptionList, { type PopoverOptionItem } from '@/components/cards/PopoverOptionList.vue';
import type { CardSort } from '@/composables/card-gallery/cardSort';
import type { HoverMode } from '@/composables/card-gallery/hoverMode';
import { HOVER_MODE_OPTIONS } from '@/composables/card-gallery/hoverMode';
import { cardSortOptions } from '@/composables/card-gallery/cardSort';
import { CARD_PAGE_SIZE_OPTIONS } from '@/composables/card-gallery/pageSize';
import { useGalleryOptions } from '@/composables/useGalleryOptions';
import { useHoverModePreferences } from '@/composables/useHoverModePreferences';
import { useCardSortPreferences } from '@/composables/useCardSortPreferences';

const { defaultSort } = useCardSortPreferences();
const { defaultHoverMode } = useHoverModePreferences();
const { cardScale, showCardGroups, pageSize } = useGalleryOptions();
const hoverModeOptions = HOVER_MODE_OPTIONS;
const cardSortMenuOptions = computed<PopoverOptionItem[]>(() =>
  cardSortOptions.map((option) => ({
    value: option.value,
    label: option.label,
    description: option.description,
  })),
);
const hoverModeMenuOptions = computed<PopoverOptionItem[]>(() =>
  hoverModeOptions.map((option) => ({
    value: option.value,
    label: option.label,
    description: option.description,
  })),
);
const cardPageSizeOptions = CARD_PAGE_SIZE_OPTIONS;
const cardPageSizeSelectOptions = computed(() =>
  cardPageSizeOptions.map((option) => ({
    value: option,
    label: `${option} cards`,
  })),
);
const percentLabel = computed(() => `${Math.round(cardScale.value * 100)}%`);

const handleDefaultHoverModeSelect = (value: string): void => {
  defaultHoverMode.value = value as HoverMode;
};

const handleDefaultSortSelect = (value: string): void => {
  defaultSort.value = value as CardSort;
};
</script>
