<template>
  <div class="pointer-events-none w-[24rem] rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-2xl backdrop-blur">
    <div class="space-y-4">
      <div>
        <h4 class="text-base font-semibold text-slate-900">
          {{ card.name || 'Unnamed Card' }}
        </h4>
        <p class="text-xs text-slate-500">
          Version {{ card.version_number }}
          <span v-if="card.is_latest"> · Latest</span>
        </p>
      </div>

      <div class="grid gap-3 text-sm text-slate-700 sm:grid-cols-2">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Type Line
          </p>
          <p>{{ card.type_line || '-' }}</p>
        </div>
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Mana
          </p>
          <SymbolizedText
            :tokens="card.mana_symbols"
            :text="card.mana_cost || '-'"
            :symbol-by-key="symbolByKey"
          />
        </div>
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Attack
          </p>
          <p>{{ card.attack ?? '-' }}</p>
        </div>
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Health
          </p>
          <p>{{ card.health ?? '-' }}</p>
        </div>
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Confidence
          </p>
          <p>{{ card.confidence.toFixed(2) }}</p>
        </div>
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Parsed
          </p>
          <p>{{ parsedAtLabel }}</p>
        </div>
      </div>

      <div class="grid gap-3 md:grid-cols-2">
        <div>
          <p class="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Keywords
          </p>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="keyword in card.keywords"
              :key="keyword"
              class="rounded bg-sky-100 px-2 py-0.5 text-[11px] text-sky-800"
            >
              {{ keyword }}
            </span>
            <span
              v-if="card.keywords.length === 0"
              class="text-[11px] text-slate-400"
            >
              None
            </span>
          </div>
        </div>

        <div>
          <p class="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Tags
          </p>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="tag in card.tags"
              :key="tag.id"
              class="rounded bg-emerald-100 px-2 py-0.5 text-[11px] text-emerald-800"
            >
              {{ tag.label }}
            </span>
            <span
              v-if="card.tags.length === 0"
              class="text-[11px] text-slate-400"
            >
              None
            </span>
          </div>
        </div>

        <div>
          <p class="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Types
          </p>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="type in card.types"
              :key="type.id"
              class="rounded bg-amber-100 px-2 py-0.5 text-[11px] text-amber-800"
            >
              {{ type.label }}
            </span>
            <span
              v-if="card.types.length === 0"
              class="text-[11px] text-slate-400"
            >
              None
            </span>
          </div>
        </div>

        <div>
          <p class="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Symbols
          </p>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="symbol in card.symbols"
              :key="symbol.id"
              class="rounded bg-violet-100 px-2 py-0.5 text-[11px] text-violet-800"
            >
              {{ symbol.label }}
            </span>
            <span
              v-if="card.symbols.length === 0"
              class="text-[11px] text-slate-400"
            >
              None
            </span>
          </div>
        </div>
      </div>

      <div>
        <p class="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
          Rules Text
        </p>
        <p class="whitespace-pre-line rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-700">
          {{ card.rules_text || '-' }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import SymbolizedText from '@/components/SymbolizedText.vue';
import type { CardGalleryItemModel } from '@/components/cards/CardGalleryItem.vue';

const props = defineProps<{
  card: CardGalleryItemModel;
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
