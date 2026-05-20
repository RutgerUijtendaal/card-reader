<template>
  <div class="theme-popover pointer-events-none w-[24rem] shadow-2xl">
    <div class="space-y-4">
      <div>
        <h4 class="theme-section-title text-base font-semibold">
          {{ card.name || 'Unnamed Card' }}
        </h4>
        <p class="theme-section-muted text-xs">
          Version {{ card.version_number }}
          <span v-if="card.is_latest"> · Latest</span>
        </p>
      </div>

      <div class="theme-section-muted grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <p class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">
            Type Line
          </p>
          <p>{{ card.type_line || '-' }}</p>
        </div>
        <div>
          <p class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">
            Mana
          </p>
          <SymbolizedText
            :tokens="card.mana_symbols"
            :text="card.mana_cost || '-'"
            :symbol-by-key="symbolByKey"
          />
        </div>
        <div>
          <p class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">
            Attack
          </p>
          <p>{{ card.attack ?? '-' }}</p>
        </div>
        <div>
          <p class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">
            Health
          </p>
          <p>{{ card.health ?? '-' }}</p>
        </div>
        <div>
          <p class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">
            Confidence
          </p>
          <p>{{ card.confidence.toFixed(2) }}</p>
        </div>
        <div>
          <p class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">
            Parsed
          </p>
          <p>{{ parsedAtLabel }}</p>
        </div>
      </div>

      <div class="grid gap-3 md:grid-cols-2">
        <div>
          <p class="theme-kicker mb-2 text-[11px] font-semibold uppercase tracking-wide">
            Keywords
          </p>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="keyword in card.keywords"
              :key="keyword"
              class="rounded bg-sky-100 px-2 py-0.5 text-[11px] text-sky-800 dark:bg-sky-950/70 dark:text-sky-100"
            >
              {{ keyword }}
            </span>
            <span
              v-if="card.keywords.length === 0"
              class="theme-kicker text-[11px]"
            >
              None
            </span>
          </div>
        </div>

        <div>
          <p class="theme-kicker mb-2 text-[11px] font-semibold uppercase tracking-wide">
            Tags
          </p>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="tag in card.tags"
              :key="tag.id"
              class="rounded bg-emerald-100 px-2 py-0.5 text-[11px] text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-100"
            >
              {{ tag.label }}
            </span>
            <span
              v-if="card.tags.length === 0"
              class="theme-kicker text-[11px]"
            >
              None
            </span>
          </div>
        </div>

        <div>
          <p class="theme-kicker mb-2 text-[11px] font-semibold uppercase tracking-wide">
            Types
          </p>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="type in card.types"
              :key="type.id"
              class="rounded bg-amber-100 px-2 py-0.5 text-[11px] text-amber-800 dark:bg-amber-950/70 dark:text-amber-100"
            >
              {{ type.label }}
            </span>
            <span
              v-if="card.types.length === 0"
              class="theme-kicker text-[11px]"
            >
              None
            </span>
          </div>
        </div>

        <div>
          <p class="theme-kicker mb-2 text-[11px] font-semibold uppercase tracking-wide">
            Symbols
          </p>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="symbol in card.symbols"
              :key="symbol.id"
              class="rounded bg-violet-100 px-2 py-0.5 text-[11px] text-violet-800 dark:bg-violet-950/70 dark:text-violet-100"
            >
              {{ symbol.label }}
            </span>
            <span
              v-if="card.symbols.length === 0"
              class="theme-kicker text-[11px]"
            >
              None
            </span>
          </div>
        </div>
      </div>

      <div>
        <p class="theme-kicker mb-2 text-[11px] font-semibold uppercase tracking-wide">
          Rules Text
        </p>
        <p class="whitespace-pre-line rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-700 dark:bg-slate-800/80 dark:text-slate-200">
          {{ card.rules_text || '-' }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import SymbolizedText from '@/components/SymbolizedText.vue';
import type { CardListItem } from '@/modules/card-detail/types';

const props = defineProps<{
  card: CardListItem;
}>();

const symbolByKey = computed(() =>
  Object.fromEntries(props.card.symbols.map((symbol) => [symbol.key, symbol])),
);

const parsedAtLabel = computed(() => {
  const parsedAt = new Date(props.card.created_at);
  if (Number.isNaN(parsedAt.getTime())) {
    return '-';
  }
  return parsedAt.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
});
</script>
