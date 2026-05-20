<template>
  <div class="page-card">
    <div class="grid gap-4 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
      <div class="theme-muted-panel p-3">
        <img
          v-if="version.image_url"
          :src="toAbsoluteApiUrl(version.image_url)"
          alt="Selected card version image"
          class="mx-auto block max-h-[38rem] w-full object-contain"
        >
        <div
          v-else
          class="theme-empty-state flex h-80 items-center justify-center"
        >
          No image
        </div>
      </div>

      <div class="space-y-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h3 class="theme-section-title text-lg font-semibold">
              {{ version.name || 'Unnamed Card' }}
            </h3>
            <p class="theme-section-muted text-sm">
              Version {{ version.version_number }}
              <span v-if="version.is_latest"> · Latest</span>
            </p>
          </div>
          <span
            v-if="showEditableState"
            class="rounded-full px-2.5 py-1 text-xs font-medium"
            :class="version.editable ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-100' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'"
          >
            {{ version.editable ? 'Editable' : 'Read-only' }}
          </span>
        </div>

        <div class="theme-section-muted grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <p class="theme-kicker text-xs font-semibold uppercase tracking-wide">
              Type Line
            </p>
            <p>{{ version.type_line || '-' }}</p>
          </div>
          <div>
            <p class="theme-kicker text-xs font-semibold uppercase tracking-wide">
              Mana
            </p>
            <SymbolizedText
              :tokens="version.mana_symbols"
              :text="version.mana_cost || '-'"
              :symbol-by-key="symbolByKey"
            />
          </div>
          <div>
            <p class="theme-kicker text-xs font-semibold uppercase tracking-wide">
              Attack
            </p>
            <p>{{ version.attack ?? '-' }}</p>
          </div>
          <div>
            <p class="theme-kicker text-xs font-semibold uppercase tracking-wide">
              Health
            </p>
            <p>{{ version.health ?? '-' }}</p>
          </div>
          <div>
            <p class="theme-kicker text-xs font-semibold uppercase tracking-wide">
              Confidence
            </p>
            <p>{{ version.confidence.toFixed(2) }}</p>
          </div>
          <div>
            <p class="theme-kicker text-xs font-semibold uppercase tracking-wide">
              Parsed
            </p>
            <p>{{ formatDate(version.created_at) }}</p>
          </div>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <div>
            <p class="theme-kicker mb-2 text-xs font-semibold uppercase tracking-wide">
              Keywords
            </p>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="keyword in version.keywords"
                :key="`keyword-${version.version_id}-${keyword}`"
                class="rounded bg-sky-100 px-2 py-0.5 text-xs text-sky-800 dark:bg-sky-950/70 dark:text-sky-100"
              >
                {{ keyword }}
              </span>
              <span
                v-if="version.keywords.length === 0"
                class="theme-kicker text-xs"
              >
                None
              </span>
            </div>
          </div>
          <div>
            <p class="theme-kicker mb-2 text-xs font-semibold uppercase tracking-wide">
              Tags
            </p>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="tag in version.tags"
                :key="tag.id"
                class="rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-100"
              >
                {{ tag.label }}
              </span>
              <span
                v-if="version.tags.length === 0"
                class="theme-kicker text-xs"
              >
                None
              </span>
            </div>
          </div>
          <div>
            <p class="theme-kicker mb-2 text-xs font-semibold uppercase tracking-wide">
              Types
            </p>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="type in version.types"
                :key="type.id"
                class="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-950/70 dark:text-amber-100"
              >
                {{ type.label }}
              </span>
              <span
                v-if="version.types.length === 0"
                class="theme-kicker text-xs"
              >
                None
              </span>
            </div>
          </div>
          <div>
            <p class="theme-kicker mb-2 text-xs font-semibold uppercase tracking-wide">
              Symbols
            </p>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="symbol in version.symbols"
                :key="symbol.id"
                class="rounded bg-violet-100 px-2 py-0.5 text-xs text-violet-800 dark:bg-violet-950/70 dark:text-violet-100"
              >
                {{ symbol.label }}
              </span>
              <span
                v-if="version.symbols.length === 0"
                class="theme-kicker text-xs"
              >
                None
              </span>
            </div>
          </div>
        </div>

        <div>
          <p class="theme-kicker mb-2 text-xs font-semibold uppercase tracking-wide">
            Rules Text
          </p>
          <p class="whitespace-pre-line rounded-lg bg-slate-50 p-3 text-sm text-slate-700 dark:bg-slate-800/80 dark:text-slate-200">
            {{ version.rules_text || '-' }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import SymbolizedText from '@/components/SymbolizedText.vue';
import type { SymbolLookupMap, CardVersionDetail } from '@/modules/card-detail/types';

withDefaults(
  defineProps<{
    version: CardVersionDetail;
    symbolByKey: SymbolLookupMap;
    toAbsoluteApiUrl: (urlPath: string) => string;
    formatDate: (value: string) => string;
    showEditableState?: boolean;
  }>(),
  {
    showEditableState: true,
  },
);
</script>
