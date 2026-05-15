<template>
  <div class="pointer-events-none w-80 rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-2xl backdrop-blur">
    <div class="space-y-3">
      <div>
        <h4 class="text-sm font-semibold text-slate-900">
          {{ card.name || 'Unnamed Card' }}
        </h4>
        <p class="text-xs text-slate-500">
          {{ card.type_line || '-' }}
        </p>
      </div>

      <div class="grid grid-cols-2 gap-3 text-xs text-slate-700">
        <div>
          <p class="font-semibold uppercase tracking-wide text-slate-400">
            Mana
          </p>
          <SymbolizedText
            :tokens="card.mana_symbols"
            :text="card.mana_cost || '-'"
            :symbol-by-key="symbolByKey"
          />
        </div>
        <div>
          <p class="font-semibold uppercase tracking-wide text-slate-400">
            Stats
          </p>
          <p>{{ card.attack ?? '-' }} / {{ card.health ?? '-' }}</p>
        </div>
      </div>

      <div
        v-if="card.rules_text"
        class="rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-700"
      >
        {{ card.rules_text }}
      </div>

      <div class="space-y-2">
        <div v-if="card.keywords.length > 0">
          <p class="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
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
          </div>
        </div>

        <div v-if="card.tags.length > 0">
          <p class="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
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
          </div>
        </div>

        <div v-if="card.types.length > 0">
          <p class="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
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
          </div>
        </div>
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
</script>
