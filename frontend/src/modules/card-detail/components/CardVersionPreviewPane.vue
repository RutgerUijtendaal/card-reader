<template>
  <div class="page-card">
    <div class="grid gap-4 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
      <div class="rounded-xl border border-slate-200 bg-slate-50 p-3">
        <img
          v-if="version.image_url"
          :src="toAbsoluteApiUrl(version.image_url)"
          alt="Selected card version image"
          class="mx-auto block max-h-[38rem] w-full object-contain"
        >
        <div
          v-else
          class="flex h-80 items-center justify-center rounded-lg border border-dashed border-slate-300 text-sm text-slate-500"
        >
          No image
        </div>
      </div>

      <div class="space-y-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h3 class="text-lg font-semibold text-slate-900">
              {{ version.name || 'Unnamed Card' }}
            </h3>
            <p class="text-sm text-slate-500">
              Version {{ version.version_number }}
              <span v-if="version.is_latest"> · Latest</span>
            </p>
          </div>
          <span
            v-if="showEditableState"
            class="rounded-full px-2.5 py-1 text-xs font-medium"
            :class="version.editable ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'"
          >
            {{ version.editable ? 'Editable' : 'Read-only' }}
          </span>
        </div>

        <div class="grid gap-3 text-sm text-slate-700 sm:grid-cols-2">
          <div>
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Type Line
            </p>
            <p>{{ version.type_line || '-' }}</p>
          </div>
          <div>
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Mana
            </p>
            <SymbolizedText
              :tokens="version.mana_symbols"
              :text="version.mana_cost || '-'"
              :symbol-by-key="symbolByKey"
            />
          </div>
          <div>
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Attack
            </p>
            <p>{{ version.attack ?? '-' }}</p>
          </div>
          <div>
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Health
            </p>
            <p>{{ version.health ?? '-' }}</p>
          </div>
          <div>
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Confidence
            </p>
            <p>{{ version.confidence.toFixed(2) }}</p>
          </div>
          <div>
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Parsed
            </p>
            <p>{{ formatDate(version.created_at) }}</p>
          </div>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <div>
            <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Keywords
            </p>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="keyword in version.keywords"
                :key="`keyword-${version.version_id}-${keyword}`"
                class="rounded bg-sky-100 px-2 py-0.5 text-xs text-sky-800"
              >
                {{ keyword }}
              </span>
              <span
                v-if="version.keywords.length === 0"
                class="text-xs text-slate-400"
              >
                None
              </span>
            </div>
          </div>
          <div>
            <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Tags
            </p>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="tag in version.tags"
                :key="tag.id"
                class="rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800"
              >
                {{ tag.label }}
              </span>
              <span
                v-if="version.tags.length === 0"
                class="text-xs text-slate-400"
              >
                None
              </span>
            </div>
          </div>
          <div>
            <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Types
            </p>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="type in version.types"
                :key="type.id"
                class="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-800"
              >
                {{ type.label }}
              </span>
              <span
                v-if="version.types.length === 0"
                class="text-xs text-slate-400"
              >
                None
              </span>
            </div>
          </div>
          <div>
            <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Symbols
            </p>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="symbol in version.symbols"
                :key="symbol.id"
                class="rounded bg-violet-100 px-2 py-0.5 text-xs text-violet-800"
              >
                {{ symbol.label }}
              </span>
              <span
                v-if="version.symbols.length === 0"
                class="text-xs text-slate-400"
              >
                None
              </span>
            </div>
          </div>
        </div>

        <div>
          <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Rules Text
          </p>
          <p class="whitespace-pre-line rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
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
