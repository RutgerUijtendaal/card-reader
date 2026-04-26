<template>
  <h4 class="text-base font-semibold text-slate-900">
    {{ item.name }}
  </h4>
  <p class="mb-3 text-xs text-slate-500">
    {{ item.type_line || 'No type' }}
  </p>

  <div class="grid grid-cols-2 gap-2 text-xs text-slate-700">
    <span
      v-if="item.version_number !== undefined"
      class="truncate"
    >
      Version: {{ item.version_number }}
    </span>
    <span>Conf: {{ item.confidence.toFixed(2) }}</span>
    <span class="inline-flex items-center gap-1">
      Mana:
      <SymbolizedText
        :tokens="item.mana_symbols"
        :text="item.mana_cost"
        :symbol-by-key="symbolByKey"
      />
    </span>
    <span
      v-if="item.created_at"
      class="truncate"
    >
      Date: {{ formatDate(item.created_at) }}
    </span>
    <span>ATK: {{ item.attack ?? '-' }}</span>
    <span>HP: {{ item.health ?? '-' }}</span>
  </div>

  <div class="mt-2 space-y-2 text-[11px]">
    <div v-if="item.tags.length">
      <p class="mb-1 font-semibold uppercase tracking-wide text-slate-400">
        Tags
      </p>
      <div class="flex flex-wrap gap-1">
        <span
          v-for="tag in item.tags"
          :key="`tag-${item.id}-${tag.id}`"
          class="rounded bg-emerald-100 px-2 py-0.5 text-emerald-800"
        >
          {{ tag.label }}
        </span>
      </div>
    </div>

    <div v-if="affinitySymbols.length">
      <p class="mb-2 font-semibold uppercase tracking-wide text-slate-400">
        Affinity
      </p>
      <div class="flex flex-wrap gap-1">
        <span
          v-for="symbol in affinitySymbols"
          :key="`symbol-${item.id}-${symbol.id}`"
          class="rounded bg-violet-100 px-2 py-0.5 text-violet-800"
        >
          {{ symbol.label }}
        </span>
      </div>
    </div>

    <div v-if="item.types.length">
      <p class="mb-2 font-semibold uppercase tracking-wide text-slate-400">
        Types
      </p>
      <div class="flex flex-wrap gap-1">
        <span
          v-for="type in item.types"
          :key="`type-${item.id}-${type.id}`"
          class="rounded bg-amber-100 px-2 py-0.5 text-amber-800"
        >
          {{ type.label }}
        </span>
      </div>
    </div>

    <div v-if="item.keywords.length">
      <p class="mb-2 font-semibold uppercase tracking-wide text-slate-400">
        Keywords
      </p>
      <div class="flex flex-wrap gap-1">
        <span
          v-for="keyword in item.keywords"
          :key="`keyword-${item.id}-${keyword}`"
          class="rounded bg-sky-100 px-2 py-0.5 text-sky-800"
        >
          {{ keyword }}
        </span>
      </div>
    </div>
  </div>
  <div class="mt-2 space-y-2 text-[11px]">
    <p class="mb-2 font-semibold uppercase tracking-wide text-slate-400">
      Rule text
    </p>
    <p
      class="mt-3 whitespace-pre-line text-xs text-slate-600"
    >
      {{ item.rules_text || '-' }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import SymbolizedText from '@/components/SymbolizedText.vue';

export type CardTooltipSymbolLookup = {
  asset_url?: string | null;
  text_token?: string;
};

export type CardTooltipMetadata = {
  id: string;
  key: string;
  label: string;
};

export type CardTooltipSymbol = CardTooltipMetadata & {
  symbol_type: string;
  text_token: string;
  asset_url: string | null;
};

export type CardHoverTooltipModel = {
  id: string;
  template_id: string;
  version_id: string;
  version_number: number;
  previous_version_id: string | null;
  is_latest: boolean;
  name: string;
  type_line: string;
  mana_cost: string;
  mana_symbols: string[];
  attack: number | null;
  health: number | null;
  rules_text: string;
  confidence: number;
  created_at: string;
  keywords: string[];
  tags: CardTooltipMetadata[];
  symbols: CardTooltipSymbol[];
  types: CardTooltipMetadata[];
};

const props = defineProps<{
  item: CardHoverTooltipModel;
  symbolByKey: Record<string, CardTooltipSymbolLookup>;
}>();

const affinitySymbols = computed(() =>
  props.item.symbols.filter((symbol) => symbol.symbol_type === 'affinity'),
);

const formatDate = (value: string): string => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString();
};
</script>
