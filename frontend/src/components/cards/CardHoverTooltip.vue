<template>
  <div
    class="theme-popover pointer-events-none shadow-2xl"
    :class="imageUrl ? 'w-[64rem]' : 'w-[35rem]'"
  >
    <div
      class="gap-4"
      :class="imageUrl ? 'grid grid-cols-[28rem_minmax(0,1fr)] items-start' : 'space-y-4'"
    >
      <div
        v-if="imageUrl"
        class="theme-card-frame theme-card-image-well overflow-hidden rounded-xl"
      >
        <div class="aspect-[63/88]">
          <img
            :src="toAbsoluteApiUrl(imageUrl)"
            :alt="imageAlt"
            class="h-full w-full object-cover"
          >
        </div>
      </div>

      <div
        class="space-y-4"
        :class="imageUrl ? 'theme-divider border-l pl-4' : ''"
      >
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <h4 class="theme-section-title text-base font-semibold">
              {{ card.name || 'Unnamed Card' }}
            </h4>
            <span
              v-if="cardIsDeprecated(card)"
              class="theme-pill theme-pill-warning px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
            >
              Deprecated
            </span>
          </div>
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
                class="theme-pill theme-pill-keyword px-2 py-0.5 text-[11px]"
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
                class="theme-pill theme-pill-success px-2 py-0.5 text-[11px]"
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
                class="theme-pill theme-pill-warning px-2 py-0.5 text-[11px]"
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
                class="theme-pill theme-pill-symbol px-2 py-0.5 text-[11px]"
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
          <p class="theme-card-frame-muted theme-section-muted whitespace-pre-line rounded-lg p-3 text-xs leading-5">
            {{ card.rules_text || '-' }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';
import SymbolizedText from '@/components/SymbolizedText.vue';
import { cardIsDeprecated } from '@/modules/card-filters/cardLifecycle';
import type { CardListItem } from '@/modules/card-detail/types';

const props = defineProps<{
  card: CardListItem;
  imageUrl?: string | null;
  imageAlt?: string;
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

const imageUrl = computed(() => props.imageUrl ?? null);
const imageAlt = computed(() => props.imageAlt ?? props.card.name ?? 'Card preview');
</script>
