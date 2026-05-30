<template>
  <div class="page-card">
    <div class="grid gap-4 lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
      <div class="theme-muted-panel p-3">
        <img
          v-if="version.image_url"
          :src="toAbsoluteApiUrl(version.image_url)"
          alt="Selected card version image"
          class="mx-auto block max-h-[42rem] w-full object-contain"
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
              Printing {{ version.version_number }}
              <span v-if="version.is_latest"> · Latest</span>
            </p>
          </div>
          <span
            v-if="showEditableState"
            class="theme-pill px-2.5 py-1 text-xs"
            :class="version.editable ? 'theme-pill-success' : 'theme-pill-neutral'"
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
                class="theme-pill theme-pill-keyword px-2 py-0.5 text-xs"
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
                class="theme-pill theme-pill-success px-2 py-0.5 text-xs"
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
                class="theme-pill theme-pill-warning px-2 py-0.5 text-xs"
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
                class="theme-pill theme-pill-symbol px-2 py-0.5 text-xs"
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
          <p class="theme-card-frame-muted theme-section-muted whitespace-pre-line rounded-lg p-3 text-sm">
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
