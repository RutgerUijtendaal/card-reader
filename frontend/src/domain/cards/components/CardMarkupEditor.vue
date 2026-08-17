<template>
  <div class="space-y-2">
    <div
      class="theme-divider flex border-b"
      role="tablist"
      :aria-label="`${label} editor mode`"
    >
      <button
        v-for="mode in modes"
        :key="mode"
        class="px-3 py-2 text-sm font-semibold"
        :class="
          activeMode === mode
            ? 'border-b-2 border-[var(--color-link)] text-[var(--color-text)]'
            : 'theme-section-muted'
        "
        type="button"
        role="tab"
        :aria-selected="activeMode === mode"
        @click="activeMode = mode"
      >
        {{ mode }}
      </button>
    </div>
    <div
      v-if="activeMode === 'Write'"
      class="relative"
    >
      <textarea
        :id="textareaId"
        ref="textareaRef"
        class="input-base resize-y"
        :class="minHeightClass"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        @input="handleInput"
        @click="refreshTrigger"
        @keyup="handleKeyup"
        @keydown="handleKeydown"
        @blur="handleBlur"
      />
      <div
        v-if="trigger"
        ref="popupRef"
        class="theme-popover absolute z-40 p-2 shadow-xl"
        :style="popupStyle"
      >
        <div class="app-scrollbar max-h-80 space-y-2 overflow-y-auto">
          <p
            v-if="searching"
            class="theme-section-muted px-2 py-2 text-sm"
          >
            Searching…
          </p>
          <template v-if="showsCards && cards.length">
            <p class="theme-kicker px-2 pt-1 text-xs font-semibold uppercase tracking-wide">
              Cards
            </p>
            <SmallCardSearchResultRow
              v-for="(card, index) in cards"
              :key="card.id"
              :card="card"
              :selected="selectedIndex === index"
              action-label="Insert"
              @pointerdown.prevent
              @activate="insertCard"
            />
          </template>
          <template v-if="showsSymbols && filteredSymbols.length">
            <p class="theme-kicker px-2 pt-1 text-xs font-semibold uppercase tracking-wide">
              Symbols
            </p>
            <button
              v-for="(symbol, index) in filteredSymbols"
              :key="symbol.id"
              class="theme-card-frame flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm"
              :class="selectedIndex === cards.length + index ? 'theme-selected-surface-strong' : ''"
              type="button"
              @pointerdown.prevent
              @click="insertSymbol(symbol)"
            >
              <span class="font-semibold">{{ symbol.label }}</span>
              <span class="theme-section-muted">{{ symbol.text_token || symbol.key }}</span>
            </button>
          </template>
          <p
            v-if="!searching && cards.length === 0 && filteredSymbols.length === 0"
            class="theme-section-muted px-2 py-3 text-sm"
          >
            No matching references.
          </p>
        </div>
      </div>
    </div>
    <div
      v-else
      class="theme-card-frame-muted min-h-24 rounded-lg p-4"
    >
      <CardMarkupText
        v-if="modelValue.trim()"
        :markup="modelValue"
        :symbols="symbols"
      />
      <p
        v-else
        class="theme-section-muted text-sm"
      >
        Nothing to preview yet.
      </p>
    </div>
    <p class="theme-section-muted text-xs">
      Markdown is supported. Type <code>[[</code> to link a card<span v-if="allowSymbols">
        or symbol</span>.
    </p>
  </div>
</template>

<script setup lang="ts">
import { useDebounceFn } from '@vueuse/core';
import { computed, nextTick, ref } from 'vue';
import CardMarkupText from '@/domain/cards/components/CardMarkupText.vue';
import SmallCardSearchResultRow from '@/domain/cards/components/SmallCardSearchResultRow.vue';
import { useCardSearchResults } from '@/domain/cards/composables/useCardSearchResults';
import type { CardListItem, SymbolFilterOption } from '@/domain/cards/types';
import {
  buildCardReference,
  buildSymbolReference,
  findCardMarkupTrigger,
  type CardMarkupTrigger,
} from '@/domain/cards/utils/cardMarkup';

const props = withDefaults(
  defineProps<{
    modelValue: string;
    label: string;
    placeholder?: string;
    symbols?: SymbolFilterOption[];
    allowSymbols?: boolean;
    includeDeprecatedCards?: boolean;
    disabled?: boolean;
  minHeightClass?: string;
  textareaId?: string;
  }>(),
  {
    placeholder: '',
    symbols: () => [],
    allowSymbols: false,
    includeDeprecatedCards: false,
    disabled: false,
  minHeightClass: 'min-h-40',
  textareaId: undefined,
  },
);

const emit = defineEmits<{ (event: 'update:modelValue', value: string): void }>();
const modes = ['Write', 'Preview'] as const;
const activeMode = ref<(typeof modes)[number]>('Write');
const textareaRef = ref<HTMLTextAreaElement | null>(null);
const popupRef = ref<HTMLElement | null>(null);
const trigger = ref<CardMarkupTrigger | null>(null);
const popupPosition = ref({ left: 0, top: 0, width: 320 });
const selectedIndex = ref(0);
const cardSearch = useCardSearchResults(() => ({
  lifecycleStatus: props.includeDeprecatedCards ? 'all' : 'active',
  pageSize: 8,
}));
const { results: cards, searching } = cardSearch;
const showsCards = computed(() => trigger.value?.kind !== 'symbol');
const showsSymbols = computed(() => props.allowSymbols && trigger.value?.kind !== 'card');
const filteredSymbols = computed(() => {
  if (!showsSymbols.value) return [];
  const query = trigger.value?.query.trim().toLowerCase() ?? '';
  return props.symbols
    .filter(
      (symbol) =>
        !query || symbol.label.toLowerCase().includes(query) || symbol.key.includes(query),
    )
    .slice(0, 8);
});
const itemCount = computed(() => cards.value.length + filteredSymbols.value.length);
const popupStyle = computed(() => ({
  left: `${popupPosition.value.left}px`,
  top: `${popupPosition.value.top}px`,
  width: `${popupPosition.value.width}px`,
}));

const runSearch = async (): Promise<void> => {
  const currentTrigger = trigger.value;
  if (!currentTrigger || currentTrigger.kind === 'symbol') {
    cardSearch.clear();
    return;
  }
  await cardSearch.search(currentTrigger.query, { allowEmpty: true });
};
const debouncedSearch = useDebounceFn(() => void runSearch(), 200);

const refreshTrigger = (): void => {
  const textarea = textareaRef.value;
  if (!textarea) return;
  trigger.value = findCardMarkupTrigger(textarea.value, textarea.selectionStart);
  selectedIndex.value = 0;
  if (!trigger.value) {
    cardSearch.clear();
    return;
  }
  popupPosition.value = measureTextareaCaret(textarea, textarea.selectionStart);
  debouncedSearch();
};
const handleInput = (event: Event): void => {
  emit('update:modelValue', (event.target as HTMLTextAreaElement).value);
  refreshTrigger();
};
const insertValue = (value: string): void => {
  const activeTrigger = trigger.value;
  if (!activeTrigger) return;
  const next = `${props.modelValue.slice(0, activeTrigger.start)}${value}${props.modelValue.slice(activeTrigger.end)}`;
  emit('update:modelValue', next);
  trigger.value = null;
  cardSearch.clear();
  void nextTick(() => {
    const caret = activeTrigger.start + value.length;
    textareaRef.value?.focus();
    textareaRef.value?.setSelectionRange(caret, caret);
  });
};
const insertCard = (card: CardListItem): void =>
  insertValue(buildCardReference(card.id, card.name || card.label));
const insertSymbol = (symbol: SymbolFilterOption): void =>
  insertValue(buildSymbolReference(symbol.key));
const insertSelected = (): void => {
  const index = selectedIndex.value;
  const card = cards.value[index];
  if (card) insertCard(card);
  else {
    const symbol = filteredSymbols.value[index - cards.value.length];
    if (symbol) insertSymbol(symbol);
  }
};
const handleKeydown = (event: KeyboardEvent): void => {
  if (!trigger.value) return;
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault();
    const delta = event.key === 'ArrowDown' ? 1 : -1;
    selectedIndex.value =
      (selectedIndex.value + delta + Math.max(itemCount.value, 1)) % Math.max(itemCount.value, 1);
  } else if ((event.key === 'Enter' || event.key === 'Tab') && itemCount.value > 0) {
    event.preventDefault();
    insertSelected();
  } else if (event.key === 'Escape') {
    event.preventDefault();
    trigger.value = null;
  }
};
const handleKeyup = (event: KeyboardEvent): void => {
  if (['ArrowDown', 'ArrowUp', 'Enter', 'Tab', 'Escape'].includes(event.key)) return;
  refreshTrigger();
};
const handleBlur = (event: FocusEvent): void => {
  const related = event.relatedTarget;
  if (!(related instanceof Node && popupRef.value?.contains(related))) trigger.value = null;
};

const measureTextareaCaret = (
  textarea: HTMLTextAreaElement,
  caret: number,
): { left: number; top: number; width: number } => {
  const mirror = document.createElement('div');
  const marker = document.createElement('span');
  const style = window.getComputedStyle(textarea);
  const copiedProperties = [
    'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
    'boxSizing', 'fontFamily', 'fontSize', 'fontStyle', 'fontWeight', 'letterSpacing',
    'lineHeight', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'textIndent', 'textTransform', 'wordSpacing',
  ] as const;
  mirror.style.position = 'absolute';
  mirror.style.left = '-9999px';
  mirror.style.top = '0';
  mirror.style.visibility = 'hidden';
  mirror.style.whiteSpace = 'pre-wrap';
  mirror.style.overflowWrap = 'break-word';
  mirror.style.width = `${textarea.offsetWidth}px`;
  for (const property of copiedProperties) mirror.style[property] = style[property];
  mirror.textContent = textarea.value.slice(0, caret);
  marker.textContent = textarea.value.slice(caret, caret + 1) || '\u200b';
  mirror.appendChild(marker);
  document.body.appendChild(mirror);
  const width = Math.min(448, textarea.clientWidth);
  const left = Math.max(
    0,
    Math.min(marker.offsetLeft - textarea.scrollLeft, textarea.clientWidth - width),
  );
  const lineHeight = Number.parseFloat(style.lineHeight) || 20;
  const top = Math.max(0, marker.offsetTop - textarea.scrollTop + lineHeight + 8);
  mirror.remove();
  return { left, top, width };
};
</script>
