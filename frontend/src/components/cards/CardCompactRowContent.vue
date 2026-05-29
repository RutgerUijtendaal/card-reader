<template>
  <div class="relative z-10 flex min-w-0 flex-1 items-center px-3 py-2">
    <div class="flex min-w-0 flex-1 flex-col justify-between self-stretch select-none pr-2">
      <div class="flex min-w-0 items-center gap-2">
        <p
          class="theme-section-title min-w-0 truncate text-sm font-semibold"
          data-testid="row-card-name"
        >
          {{ card.name }}
        </p>
        <p
          v-if="card.lifecycle_status === 'deprecated'"
          class="theme-pill theme-pill-warning inline-flex shrink-0 items-center gap-1 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
        >
          <TriangleAlert class="h-3 w-3" />
          <span>Deprecated</span>
        </p>
      </div>

      <div
        v-if="showManaSymbols"
        data-testid="row-mana-symbols"
        class="card-compact-row-mana inline-flex max-w-full items-center overflow-hidden"
      >
        <SymbolizedText
          :tokens="card.mana_symbols"
          :text="card.mana_cost || '-'"
          :symbol-by-key="manaSymbolByKey"
        />
      </div>
    </div>
  </div>

  <div
    v-if="card.image_url"
    class="theme-divider card-compact-row-art relative z-10 h-full shrink-0 overflow-hidden"
    :style="{ width: artWidth }"
  >
    <img
      :src="toAbsoluteApiUrl(card.image_url)"
      :alt="card.name"
      class="h-full w-full object-cover opacity-95"
      :style="{ objectPosition: artObjectPosition, transform: artTransform }"
    >
    <div
      class="absolute inset-y-0 left-0 w-[42%]"
      style="background: linear-gradient(to right, var(--color-surface-strong) 0%, color-mix(in srgb, var(--color-surface-strong) 92%, transparent 8%) 18%, color-mix(in srgb, var(--color-surface-strong) 74%, transparent 26%) 42%, color-mix(in srgb, var(--color-surface-strong) 46%, transparent 54%) 72%, transparent 100%);"
    />
    <div class="absolute inset-0 bg-gradient-to-l from-slate-950/70 via-slate-950/30 to-transparent" />
  </div>
  <div
    v-else
    class="theme-divider card-compact-row-art relative z-10 h-full shrink-0 border-l bg-gradient-to-l from-slate-800/35 via-slate-700/12 to-transparent"
    :style="{ width: artWidth }"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { TriangleAlert } from 'lucide-vue-next';
import { toAbsoluteApiUrl } from '@/api/client';
import SymbolizedText from '@/components/SymbolizedText.vue';
import type { CardHoverTooltipModel } from '@/components/cards/cardModels';

type CardCompactRowCard = Pick<
  CardHoverTooltipModel,
  'name' | 'mana_cost' | 'mana_symbols' | 'mana_value' | 'symbols' | 'lifecycle_status'
> & {
  image_url: string | null;
};

const props = withDefaults(defineProps<{
  card: CardCompactRowCard;
  artWidth?: string;
  artObjectPosition?: string;
  artTransform?: string;
}>(), {
  artWidth: '6rem',
  artObjectPosition: '52% 5%',
  artTransform: 'scale(1.4)',
});

const manaSymbolByKey = computed(() =>
  Object.fromEntries(props.card.symbols.map((symbol) => [symbol.key, symbol])),
);
const showManaSymbols = computed(() => props.card.mana_value !== 0 && props.card.mana_cost !== '0');
</script>

<style scoped>
.card-compact-row-mana :deep(span.inline-flex) {
  gap: 0;
  flex-wrap: nowrap;
}

.card-compact-row-mana :deep(img) {
  height: 1rem;
  width: 1rem;
}

.card-compact-row-art img {
  transform-origin: center;
}
</style>
