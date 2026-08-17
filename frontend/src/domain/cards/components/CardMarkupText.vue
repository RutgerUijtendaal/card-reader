<!-- eslint-disable vue/no-v-html -- HTML is sanitized by DOMPurify before rendering. -->
<template>
  <div
    v-bind="$attrs"
    class="card-markup-text"
    @click="handleClick"
    @keydown="handleKeydown"
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
      @pointerleave="closePreview"
      @focusout="handlePanelFocusOut"
    >
      <CardHoverTooltip
        v-if="hoverCard && showsImage && showsDetails"
        :card="hoverCard"
        :image-url="hoverCard.image_url"
        :details-revealed="true"
        :hover-preview-scale="hoverPreviewScale"
      />
      <div
        v-else-if="hoverCard && showsImage && hoverCard.image_url"
        class="theme-card-frame pointer-events-none overflow-hidden rounded-xl shadow-2xl"
        :style="enlargedPreviewStyle"
      >
        <div class="theme-card-image-well aspect-[63/88]">
          <img
            :src="toAbsoluteApiUrl(hoverCard.image_url)"
            :alt="hoverCard.name || 'Card preview'"
            class="h-full w-full object-cover"
          >
        </div>
      </div>
      <CardHoverTooltip
        v-else-if="hoverCard && showsDetails"
        :card="hoverCard"
        :details-revealed="true"
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
import { toAbsoluteApiUrl } from '@/shared/api/client';
import CardHoverTooltip from '@/domain/cards/components/CardHoverTooltip.vue';
import { useHoverModePreferences } from '@/domain/cards/composables/useHoverModePreferences';
import type { SymbolFilterOption, CardListItem } from '@/domain/cards/types';
import { fetchHoverPreviewCard } from '@/domain/cards/utils/cardHoverPreview';
import { renderCardMarkupHtml } from '@/domain/cards/utils/cardMarkup';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';
import { getHoverPreviewCardWidthRem } from '@/domain/cards/utils/gallery/hoverPreviewScale';

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
const enlargedPreviewStyle = computed(() => ({
  width: `${getHoverPreviewCardWidthRem(hoverPreviewScale.value)}rem`,
}));
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
const linkFromEvent = (event: Event): HTMLAnchorElement | null => {
  const target = event.target;
  return target instanceof Element ? target.closest<HTMLAnchorElement>('a') : null;
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
  closePreview();
};
const closePreview = (): void => {
  activeCardId.value = null;
  triggerRef.value = null;
};
const handleClick = (event: MouseEvent): void => {
  if (linkFromEvent(event)) event.stopPropagation();
};
const handleKeydown = (event: KeyboardEvent): void => {
  if (linkFromEvent(event) && (event.key === 'Enter' || event.key === ' ')) {
    event.stopPropagation();
  }
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
const handlePanelFocusOut = (event: FocusEvent): void => {
  const related = event.relatedTarget;
  if (related instanceof Node && (
    panelRef.value?.contains(related) || triggerRef.value?.contains(related)
  )) return;
  closePreview();
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
