<!-- eslint-disable vue/no-v-html -- HTML is sanitized by DOMPurify before rendering. -->
<template>
  <div
    v-bind="$attrs"
    class="card-markup-text"
    @click="handleClick"
    @pointerover="handlePointerOver"
    @pointerout="handlePointerOut"
    @focusin="handleFocusIn"
    @focusout="handleFocusOut"
    v-html="renderedHtml"
  />

  <Teleport to="body">
    <div
      v-if="showPreview"
      ref="panelRef"
      class="z-50"
      :style="{ position: 'fixed', left: `${x}px`, top: `${y}px` }"
    >
      <CardHoverTooltip
        v-if="hoverCard"
        :card="hoverCard"
        :image-url="showsImage ? hoverCard.image_url : null"
        :details-revealed="showsDetails"
        :hover-preview-scale="hoverPreviewScale"
      />
      <div
        v-else
        class="theme-popover max-w-xs p-3 text-sm"
      >
        {{ loading ? 'Loading card…' : 'This card is unavailable.' }}
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from '@floating-ui/vue';
import { computed, ref } from 'vue';
import CardHoverTooltip from '@/domain/cards/components/CardHoverTooltip.vue';
import { useHoverModePreferences } from '@/domain/cards/composables/useHoverModePreferences';
import type { SymbolFilterOption, CardListItem } from '@/domain/cards/types';
import { fetchHoverPreviewCard } from '@/domain/cards/utils/cardHoverPreview';
import { renderCardMarkupHtml } from '@/domain/cards/utils/cardMarkup';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';

defineOptions({ inheritAttrs: false });

const props = withDefaults(
  defineProps<{
    markup: string;
    symbols?: SymbolFilterOption[];
    hoverMode?: HoverMode;
  }>(),
  {
    symbols: () => [],
    hoverMode: undefined,
  },
);

const renderedHtml = computed(() => renderCardMarkupHtml(props.markup, props.symbols));
const triggerRef = ref<HTMLElement | null>(null);
const panelRef = ref<HTMLElement | null>(null);
const hoverCard = ref<CardListItem | null>(null);
const activeCardId = ref<string | null>(null);
const loading = ref(false);
const preferences = useHoverModePreferences();
const requestedMode = computed<HoverMode>(() => {
  const mode =
    props.hoverMode ??
    (preferences.hasSavedDefaultHoverMode.value ? preferences.defaultHoverMode.value : 'enlarged');
  return mode === 'none' ? 'enlarged' : mode;
});
const effectiveMode = computed<HoverMode>(() => {
  if (requestedMode.value === 'enlarged' && hoverCard.value && !hoverCard.value.image_url)
    return 'details';
  return requestedMode.value;
});
const showsImage = computed(
  () => effectiveMode.value === 'enlarged' || effectiveMode.value === 'enlarged-details',
);
const showsDetails = computed(
  () => effectiveMode.value === 'details' || effectiveMode.value === 'enlarged-details',
);
const showPreview = computed(() => activeCardId.value !== null);
const { hoverPreviewScale } = preferences;
const floating = useFloating(triggerRef, panelRef, {
  open: showPreview,
  placement: 'right-start',
  strategy: 'fixed',
  middleware: [offset(12), flip(), shift({ padding: 12 })],
  whileElementsMounted: autoUpdate,
});
const x = computed(() => floating.x.value ?? 0);
const y = computed(() => floating.y.value ?? 0);

const referenceFromEvent = (event: Event): HTMLAnchorElement | null => {
  const target = event.target;
  return target instanceof Element
    ? target.closest<HTMLAnchorElement>('a[data-card-reference-id]')
    : null;
};
const openReference = (anchor: HTMLAnchorElement): void => {
  const cardId = anchor.dataset.cardReferenceId;
  if (!cardId) return;
  triggerRef.value = anchor;
  activeCardId.value = cardId;
  hoverCard.value = null;
  loading.value = true;
  void fetchHoverPreviewCard(cardId)
    .then((card) => {
      if (activeCardId.value === cardId) hoverCard.value = card;
    })
    .finally(() => {
      if (activeCardId.value === cardId) loading.value = false;
    });
};
const closeReference = (event: Event): void => {
  const related = 'relatedTarget' in event ? event.relatedTarget : null;
  if (related instanceof Node && panelRef.value?.contains(related)) return;
  activeCardId.value = null;
  triggerRef.value = null;
};
const handleClick = (event: MouseEvent): void => {
  if (referenceFromEvent(event)) event.stopPropagation();
};
const handlePointerOver = (event: PointerEvent): void => {
  const reference = referenceFromEvent(event);
  if (reference) openReference(reference);
};
const handlePointerOut = (event: PointerEvent): void => {
  if (referenceFromEvent(event)) closeReference(event);
};
const handleFocusIn = (event: FocusEvent): void => {
  const reference = referenceFromEvent(event);
  if (reference) openReference(reference);
};
const handleFocusOut = (event: FocusEvent): void => {
  if (referenceFromEvent(event)) closeReference(event);
};
</script>

<style scoped>
.card-markup-text {
  color: var(--color-text);
  line-height: 1.65;
  overflow-wrap: anywhere;
}
.card-markup-text :deep(p + p),
.card-markup-text :deep(p + ul),
.card-markup-text :deep(p + ol),
.card-markup-text :deep(pre),
.card-markup-text :deep(blockquote) {
  margin-top: 0.85rem;
}
.card-markup-text :deep(h1),
.card-markup-text :deep(h2),
.card-markup-text :deep(h3) {
  color: var(--color-text);
  font-weight: 700;
  margin: 1rem 0 0.4rem;
}
.card-markup-text :deep(ul) {
  list-style: disc;
  padding-left: 1.4rem;
}
.card-markup-text :deep(ol) {
  list-style: decimal;
  padding-left: 1.4rem;
}
.card-markup-text :deep(blockquote) {
  border-left: 3px solid var(--color-border);
  color: var(--color-text-muted);
  padding-left: 0.85rem;
}
.card-markup-text :deep(code) {
  background: var(--color-surface-muted);
  border-radius: 0.3rem;
  padding: 0.1rem 0.3rem;
}
.card-markup-text :deep(pre) {
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: 0.65rem;
  overflow-x: auto;
  padding: 0.8rem;
}
.card-markup-text :deep(pre code) {
  background: transparent;
  padding: 0;
}
.card-markup-text :deep(a) {
  color: var(--color-link);
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 0.15em;
}
</style>
