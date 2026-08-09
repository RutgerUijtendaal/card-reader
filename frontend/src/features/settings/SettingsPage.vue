<template>
  <section class="flex w-full flex-col gap-6">
    <AppPageHeader
      :icon="SlidersHorizontal"
      title="Settings"
      subtitle="Configure default browsing and viewing preferences."
      title-tag="h2"
      title-class="text-xl"
    />

    <AppPageLayout
      columns="one"
      root-class="app-page-layout-standard"
    >
      <template #aside>
        <AppStickyAside>
          <AppSideNav
            title="Preferences"
            description="Personal preferences and developer tools."
            navigation-label="Settings sections"
          >
            <AppSideNavItem
              v-for="section in settingsSections"
              :key="section.id"
              :to="settingsSectionLocation(section.id)"
              :label="section.label"
              :description="section.summary"
              :icon="section.icon"
              :active="activeSection === section.id"
            />
          </AppSideNav>
        </AppStickyAside>
      </template>

      <section class="pt-0">
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
              :min="GALLERY_CARD_SCALE_MIN"
              :max="GALLERY_CARD_SCALE_MAX"
              :step="GALLERY_CARD_SCALE_STEP"
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
          v-else-if="activeSection === 'hover'"
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

          <div class="theme-divider border-t py-4">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="theme-section-title text-sm font-semibold">
                  Hover Card Size
                </p>
                <p class="theme-section-muted mt-1 text-sm">
                  Scale enlarged card previews shown on hover.
                </p>
              </div>
              <span class="theme-section-muted text-sm font-medium">
                {{ hoverPreviewScaleLabel }}
              </span>
            </div>
            <input
              v-model.number="hoverPreviewScale"
              type="range"
              :min="HOVER_PREVIEW_SCALE_MIN"
              :max="HOVER_PREVIEW_SCALE_MAX"
              :step="HOVER_PREVIEW_SCALE_STEP"
              class="theme-range mt-3 w-full"
            >
          </div>
        </section>

        <DeveloperDataSettingsSection
          v-else-if="activeSection === 'developer-data' && auth.canDownloadDeveloperData"
          :can-manage="auth.canManageDeveloperData"
        />
      </section>
    </AppPageLayout>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { ArrowUpDown, Database, Eye, MousePointer2, SlidersHorizontal } from 'lucide-vue-next';
import type { Component } from 'vue';
import { useRoute } from 'vue-router';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppSelect from '@/shared/components/app/AppSelect.vue';
import AppSideNav from '@/shared/components/app/AppSideNav.vue';
import AppSideNavItem from '@/shared/components/app/AppSideNavItem.vue';
import AppStickyAside from '@/shared/components/app/AppStickyAside.vue';
import { useAuthStore } from '@/domain/session/store';
import DeveloperDataSettingsSection from './components/DeveloperDataSettingsSection.vue';
import type { PopoverOptionItem } from '@/domain/cards/components/PopoverOptionList.vue';
import type { CardSort } from '@/domain/cards/utils/gallery/cardSort';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';
import { HOVER_MODE_OPTIONS } from '@/domain/cards/utils/gallery/hoverMode';
import { HOVER_PREVIEW_SCALE_MAX, HOVER_PREVIEW_SCALE_MIN, HOVER_PREVIEW_SCALE_STEP } from '@/domain/cards/utils/gallery/hoverPreviewScale';
import { cardSortOptions } from '@/domain/cards/utils/gallery/cardSort';
import { CARD_PAGE_SIZE_OPTIONS } from '@/domain/cards/utils/gallery/pageSize';
import {
  GALLERY_CARD_SCALE_MAX,
  GALLERY_CARD_SCALE_MIN,
  GALLERY_CARD_SCALE_STEP,
  useGalleryOptions,
} from '@/domain/cards/composables/useGalleryOptions';
import { useHoverModePreferences } from '@/domain/cards/composables/useHoverModePreferences';
import { useCardSortPreferences } from '@/domain/cards/composables/useCardSortPreferences';
import {
  buildSettingsTabLocation,
  parseSettingsTab,
  type SettingsTab,
} from './routeState';

type SettingsSectionId = SettingsTab;

type SettingsSection = {
  id: SettingsSectionId;
  label: string;
  summary: string;
  description: string;
  icon: Component;
};

const { defaultSort } = useCardSortPreferences();
const route = useRoute();
const auth = useAuthStore();
const { defaultHoverMode, hoverPreviewScale } = useHoverModePreferences();
const { cardScale, showCardGroups, pageSize } = useGalleryOptions();
const preferenceSections: SettingsSection[] = [
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
const developerDataSection: SettingsSection = {
  id: 'developer-data',
  label: 'Developer Data',
  summary: 'Bootstrap a checkout',
  description: 'Download the reviewed dataset, create a bootstrap code, or publish a new staff build.',
  icon: Database,
};
const settingsSections = computed<SettingsSection[]>(() =>
  auth.canDownloadDeveloperData
    ? [...preferenceSections, developerDataSection]
    : preferenceSections,
);
const activeSection = computed<SettingsSectionId>(() =>
  parseSettingsTab(route.query, {
    allowDeveloperData: auth.canDownloadDeveloperData,
  }),
);
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
const hoverPreviewScaleLabel = computed(() => `${Math.round(hoverPreviewScale.value * 100)}%`);
const activeSectionDetails = computed(
  () => settingsSections.value.find((section) => section.id === activeSection.value) ?? settingsSections.value[0]!,
);
const settingsSectionLocation = (sectionId: SettingsSectionId) =>
  buildSettingsTabLocation(sectionId, route.query);

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
