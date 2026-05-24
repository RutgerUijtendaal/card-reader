<template>
  <section class="flex w-full flex-col gap-6">
    <div class="page-card flex flex-col gap-3">
      <div class="flex items-center gap-2">
        <SlidersHorizontal class="theme-section-muted h-5 w-5" />
        <h2 class="theme-section-title text-xl font-semibold">
          Settings
        </h2>
      </div>
      <p class="theme-section-muted text-sm">
        Configure default browsing and viewing preferences.
      </p>
    </div>

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
        <div>
          <h4 class="theme-section-title text-sm font-semibold">
            Default Card Sort
          </h4>
          <p class="theme-section-muted mt-1 text-sm">
            Used by card-browsing screens unless that screen has its own override selected.
          </p>
        </div>

        <div class="space-y-2">
          <label
            v-for="option in cardSortOptions"
            :key="option.value"
            class="theme-card-frame flex cursor-pointer items-start justify-between gap-3 rounded-xl px-4 py-3 transition hover:-translate-y-0.5"
            :class="defaultSort === option.value ? 'theme-selected-surface-strong' : ''"
          >
            <div class="min-w-0">
              <p class="theme-section-title text-sm font-semibold">
                {{ option.label }}
              </p>
              <p class="theme-section-muted mt-1 text-sm">
                {{ option.description }}
              </p>
            </div>
            <div class="flex shrink-0 items-center gap-2 pt-0.5">
              <Check
                v-if="defaultSort === option.value"
                class="h-4 w-4"
              />
              <input
                :checked="defaultSort === option.value"
                type="radio"
                name="default-card-sort"
                class="theme-checkbox h-4 w-4 rounded-full border-slate-300"
                @change="defaultSort = option.value"
              >
            </div>
          </label>
        </div>
      </div>

      <div class="theme-divider space-y-4 border-t pt-5">
        <div>
          <h4 class="theme-section-title text-sm font-semibold">
            View Options
          </h4>
          <p class="theme-section-muted mt-1 text-sm">
            These control how cards appear when browsing the gallery and deck builder.
          </p>
        </div>

        <label class="flex items-start justify-between gap-4">
          <div>
            <p class="theme-section-title text-sm font-semibold">
              Tooltip
            </p>
            <p class="theme-section-muted mt-1 text-sm">
              Show card details when hovering over a card.
            </p>
          </div>
          <input
            v-model="tooltipEnabled"
            type="checkbox"
            class="theme-checkbox mt-1 h-4 w-4 rounded border-slate-300"
          >
        </label>

        <label class="flex items-start justify-between gap-4">
          <div>
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
            class="theme-checkbox mt-1 h-4 w-4 rounded border-slate-300"
          >
        </label>

        <label class="field-label">
          Cards Per Page
          <select
            v-model.number="pageSize"
            class="input-base"
          >
            <option
              v-for="option in cardPageSizeOptions"
              :key="option"
              :value="option"
            >
              {{ option }} cards
            </option>
          </select>
          <span class="theme-section-muted text-sm">
            Default gallery request size for card browsing.
          </span>
        </label>

        <div class="space-y-2">
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
            class="theme-range w-full"
          >
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Check, SlidersHorizontal } from 'lucide-vue-next';
import { cardSortOptions } from '@/modules/card-search/cardSort';
import { CARD_PAGE_SIZE_OPTIONS } from '@/modules/card-search/pageSize';
import { useGalleryOptions } from '@/modules/card-search/useGalleryOptions';
import { useCardSortPreferences } from '@/modules/card-search/useCardSortPreferences';

const { defaultSort } = useCardSortPreferences();
const { tooltipEnabled, cardScale, showCardGroups, pageSize } = useGalleryOptions();
const cardPageSizeOptions = CARD_PAGE_SIZE_OPTIONS;
const percentLabel = computed(() => `${Math.round(cardScale.value * 100)}%`);
</script>
