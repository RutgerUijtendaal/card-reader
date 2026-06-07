<template>
  <section class="flex h-[calc(100vh-3rem)] min-h-0 w-full flex-col gap-6 overflow-hidden">
    <AppPageHeader
      :icon="SlidersHorizontal"
      title="Settings"
      subtitle="Configure default browsing and viewing preferences."
      title-tag="h2"
      title-class="text-xl"
    />

    <div class="mx-auto grid min-h-0 w-full max-w-5xl flex-1 gap-5 overflow-hidden lg:grid-cols-[16rem_minmax(0,42rem)]">
      <aside class="flex min-h-0 flex-col overflow-hidden">
        <div class="mb-3 px-1">
          <h3 class="theme-section-title text-sm font-semibold">
            Card Browsing
          </h3>
          <p class="theme-section-muted mt-1 text-xs">
            Defaults for shared card list preferences.
          </p>
        </div>

        <nav
          class="app-scrollbar flex min-h-0 flex-col gap-2 overflow-y-auto pr-1"
          aria-label="Settings sections"
        >
          <button
            v-for="section in settingsSections"
            :key="section.id"
            type="button"
            class="rounded-lg border px-3 py-3 text-left transition"
            :class="activeSection === section.id
              ? 'theme-selected-surface-strong'
              : 'theme-card-frame theme-section-title hover:border-[var(--theme-border-strong)]'"
            @click="activeSection = section.id"
          >
            <div class="flex items-start gap-3">
              <component
                :is="section.icon"
                class="mt-0.5 h-4 w-4 shrink-0"
              />
              <span class="min-w-0">
                <span class="block truncate text-sm font-semibold">{{ section.label }}</span>
                <span
                  class="mt-1 block truncate text-xs"
                  :class="activeSection === section.id ? 'theme-section-title' : 'theme-section-muted'"
                >
                  {{ section.summary }}
                </span>
              </span>
            </div>
          </button>
        </nav>
      </aside>

      <section class="theme-divider app-scrollbar min-h-0 overflow-y-auto border-t pt-5 lg:border-l lg:border-t-0 lg:py-1 lg:pl-6">
        <div class="mb-5 flex items-start gap-3">
          <div
            class="theme-card-frame-muted theme-section-title flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
            aria-hidden="true"
          >
            <component
              :is="activeSectionDetails.icon"
              class="h-5 w-5"
            />
          </div>
          <div class="min-w-0">
            <h3 class="theme-section-title text-base font-semibold">
              {{ activeSectionDetails.label }}
            </h3>
            <p class="theme-section-muted mt-1 text-sm">
              {{ activeSectionDetails.description }}
            </p>
          </div>
        </div>

        <section
          v-if="activeSection === 'display'"
          class="theme-divider border-t"
        >
          <label class="flex items-start justify-between gap-4 py-4">
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

          <div class="theme-divider border-t py-4">
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

          <div class="theme-divider border-t py-4">
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
        </section>

        <section
          v-else-if="activeSection === 'sort'"
          class="space-y-3"
        >
          <div class="space-y-1">
            <p class="theme-section-title text-sm font-semibold">
              Default Card Sort
            </p>
            <p class="theme-section-muted text-xs">
              Used by card-browsing screens unless that screen has its own override selected.
            </p>
          </div>

          <div class="theme-divider border-t">
            <button
              v-for="(option, index) in cardSortMenuOptions"
              :key="option.value"
              type="button"
              class="settings-option-row theme-divider flex w-full items-start justify-between gap-3 py-4 text-left transition hover:text-[var(--color-text-strong)]"
              :class="[
                index > 0 ? 'border-t' : '',
                defaultSort === option.value ? 'settings-option-row-selected theme-section-title' : 'theme-section-muted',
              ]"
              @click="handleDefaultSortSelect(option.value)"
            >
              <span class="min-w-0">
                <span class="block text-sm font-semibold">{{ option.label }}</span>
                <span
                  v-if="option.description"
                  class="theme-section-muted mt-1 block text-xs"
                >
                  {{ option.description }}
                </span>
              </span>
              <span
                v-if="defaultSort === option.value"
                class="theme-pill theme-pill-keyword shrink-0 px-2 py-0.5 text-[11px] font-semibold"
              >
                Selected
              </span>
            </button>
          </div>
        </section>

        <section
          v-else
          class="space-y-3"
        >
          <div class="space-y-1">
            <p class="theme-section-title text-sm font-semibold">
              Default Hover Preview
            </p>
            <p class="theme-section-muted text-xs">
              Choose the default card hover behavior for gallery and deck browsing views.
            </p>
          </div>

          <div class="theme-divider border-t">
            <button
              v-for="(option, index) in hoverModeMenuOptions"
              :key="option.value"
              type="button"
              class="settings-option-row theme-divider flex w-full items-start justify-between gap-3 py-4 text-left transition hover:text-[var(--color-text-strong)]"
              :class="[
                index > 0 ? 'border-t' : '',
                defaultHoverMode === option.value ? 'settings-option-row-selected theme-section-title' : 'theme-section-muted',
              ]"
              @click="handleDefaultHoverModeSelect(option.value)"
            >
              <span class="min-w-0">
                <span class="block text-sm font-semibold">{{ option.label }}</span>
                <span
                  v-if="option.description"
                  class="theme-section-muted mt-1 block text-xs"
                >
                  {{ option.description }}
                </span>
              </span>
              <span
                v-if="defaultHoverMode === option.value"
                class="theme-pill theme-pill-keyword shrink-0 px-2 py-0.5 text-[11px] font-semibold"
              >
                Selected
              </span>
            </button>
          </div>
        </section>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { ArrowUpDown, Eye, MousePointer2, SlidersHorizontal } from 'lucide-vue-next';
import type { Component } from 'vue';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import AppSelect from '@/components/app/AppSelect.vue';
import type { PopoverOptionItem } from '@/components/cards/PopoverOptionList.vue';
import type { CardSort } from '@/composables/card-gallery/cardSort';
import type { HoverMode } from '@/composables/card-gallery/hoverMode';
import { HOVER_MODE_OPTIONS } from '@/composables/card-gallery/hoverMode';
import { cardSortOptions } from '@/composables/card-gallery/cardSort';
import { CARD_PAGE_SIZE_OPTIONS } from '@/composables/card-gallery/pageSize';
import { useGalleryOptions } from '@/composables/useGalleryOptions';
import { useHoverModePreferences } from '@/composables/useHoverModePreferences';
import { useCardSortPreferences } from '@/composables/useCardSortPreferences';

type SettingsSectionId = 'display' | 'sort' | 'hover';

type SettingsSection = {
  id: SettingsSectionId;
  label: string;
  summary: string;
  description: string;
  icon: Component;
};

const { defaultSort } = useCardSortPreferences();
const { defaultHoverMode } = useHoverModePreferences();
const { cardScale, showCardGroups, pageSize } = useGalleryOptions();
const activeSection = ref<SettingsSectionId>('display');
const settingsSections: SettingsSection[] = [
  {
    id: 'display',
    label: 'Display',
    summary: 'Layout and sizing',
    description: 'Control the default gallery layout, request size, and card thumbnail scale.',
    icon: Eye,
  },
  {
    id: 'sort',
    label: 'Sort',
    summary: 'Default ordering',
    description: 'Choose the default order used by shared card-browsing screens.',
    icon: ArrowUpDown,
  },
  {
    id: 'hover',
    label: 'Hover',
    summary: 'Preview behavior',
    description: 'Set the default card hover behavior for gallery and deck browsing views.',
    icon: MousePointer2,
  },
];
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
const activeSectionDetails = computed(
  () => settingsSections.find((section) => section.id === activeSection.value) ?? settingsSections[0],
);

const handleDefaultHoverModeSelect = (value: string): void => {
  defaultHoverMode.value = value as HoverMode;
};

const handleDefaultSortSelect = (value: string): void => {
  defaultSort.value = value as CardSort;
};
</script>

<style scoped>
.settings-option-row {
  border-left: 3px solid transparent;
  padding-left: 0.75rem;
}

.settings-option-row-selected {
  border-left-color: var(--color-selected-border);
  color: var(--color-selected-text);
}
</style>
