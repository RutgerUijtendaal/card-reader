<template>
  <div class="grid items-start gap-6 lg:grid-cols-[minmax(22rem,34rem)_minmax(24rem,1fr)]">
    <div class="theme-muted-panel p-4">
      <img
        v-if="version.image_url"
        :src="toAbsoluteApiUrl(version.image_url)"
        alt="Selected card printing image"
        class="mx-auto block max-h-[50rem] w-full object-contain"
      >
      <div
        v-else
        class="theme-empty-state flex h-80 items-center justify-center"
      >
        No image
      </div>
    </div>

    <section class="space-y-6">
      <div>
        <h3 class="theme-section-title text-2xl font-semibold">
          {{ version.name || 'Unnamed Card' }}
        </h3>
        <p class="theme-kicker mt-1 text-xs font-semibold uppercase tracking-[0.16em]">
          Printing {{ version.version_number }}<span v-if="version.is_latest"> · Latest</span>
        </p>
      </div>

      <div class="card-public-info-panels space-y-5">
        <div class="theme-card-frame-muted flex gap-4 rounded-lg p-4">
          <Sparkles class="mt-0.5 h-4 w-4 shrink-0 text-[var(--theme-accent)]" />
          <div class="min-w-0">
            <p class="theme-section-title text-xs font-semibold uppercase tracking-wide">
              Mana
            </p>
            <SymbolizedText
              :tokens="version.mana_symbols"
              :text="version.mana_cost || '-'"
              :symbol-by-key="symbolByKey"
              class="theme-section-title mt-1 text-sm"
            />
          </div>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <div class="theme-card-frame-muted rounded-lg p-4">
            <div class="theme-section-title mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide">
              <ScrollText class="h-4 w-4 shrink-0 text-[var(--theme-accent)]" />
              <span>Type</span>
            </div>
            <div class="flex flex-wrap gap-1.5">
              <span
                v-for="type in version.types"
                :key="type.id"
                class="theme-pill theme-pill-warning px-2 py-0.5 text-xs font-semibold shadow-sm ring-1 ring-[var(--color-border-strong)]"
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

          <div class="theme-card-frame-muted rounded-lg p-4">
            <div class="theme-section-title mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide">
              <Tags class="h-4 w-4 shrink-0 text-[var(--theme-accent)]" />
              <span>Tags</span>
            </div>
            <div class="flex flex-wrap gap-1.5">
              <span
                v-for="tag in version.tags"
                :key="tag.id"
                class="theme-pill theme-pill-success px-2 py-0.5 text-xs font-semibold shadow-sm ring-1 ring-[var(--color-border-strong)]"
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
        </div>

        <div>
          <div class="theme-section-title mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide">
            <BookOpenText class="h-4 w-4 shrink-0 text-[var(--theme-accent)]" />
            <span>Rules Text</span>
          </div>
          <p class="theme-card-frame-muted theme-section-muted whitespace-pre-line rounded-lg p-4 text-sm leading-6">
            {{ version.rules_text || '-' }}
          </p>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <div class="theme-card-frame-muted flex gap-4 rounded-lg p-4">
            <Swords class="mt-0.5 h-4 w-4 shrink-0 text-[var(--theme-accent)]" />
            <div class="min-w-0">
              <p class="theme-section-title text-xs font-semibold uppercase tracking-wide">
                Attack
              </p>
              <p class="theme-section-title mt-1 text-sm">
                {{ version.attack ?? '-' }}
              </p>
            </div>
          </div>
          <div class="theme-card-frame-muted flex gap-4 rounded-lg p-4">
            <HeartPulse class="mt-0.5 h-4 w-4 shrink-0 text-[var(--theme-accent)]" />
            <div class="min-w-0">
              <p class="theme-section-title text-xs font-semibold uppercase tracking-wide">
                Health
              </p>
              <p class="theme-section-title mt-1 text-sm">
                {{ version.health ?? '-' }}
              </p>
            </div>
          </div>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <div class="theme-card-frame-muted rounded-lg p-4">
            <div class="theme-section-title mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide">
              <KeyRound class="h-4 w-4 shrink-0 text-[var(--theme-accent)]" />
              <span>Keywords</span>
            </div>
            <div class="flex flex-wrap gap-1.5">
              <span
                v-for="keyword in version.keywords"
                :key="`keyword-${keyword}`"
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

          <div class="theme-card-frame-muted rounded-lg p-4">
            <div class="theme-section-title mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide">
              <Hash class="h-4 w-4 shrink-0 text-[var(--theme-accent)]" />
              <span>Symbols</span>
            </div>
            <div class="flex flex-wrap gap-1.5">
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
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { BookOpenText, Hash, HeartPulse, KeyRound, ScrollText, Sparkles, Swords, Tags } from 'lucide-vue-next';
import SymbolizedText from '@/components/SymbolizedText.vue';
import type { CardVersionDetail, SymbolLookupMap } from '@/modules/card-detail/types';

defineProps<{
  version: CardVersionDetail;
  symbolByKey: SymbolLookupMap;
  toAbsoluteApiUrl: (urlPath: string) => string;
}>();
</script>

<style scoped>
.card-public-info-panels :deep(.theme-card-frame-muted) {
  background: transparent;
  box-shadow: none;
}
</style>
