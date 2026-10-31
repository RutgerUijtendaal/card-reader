<template>
  <aside
    class="app-sticky-aside app-sticky-aside-right page-card flex min-h-0 flex-col overflow-hidden p-0"
  >
    <CardBuilderSummaryHeader
      :name="editor.form.name || 'Untitled Encounter'"
      :card="editor.boss.value"
      board-label="Mainboard"
      :count="editor.total.value"
      empty-label="Choose boss"
      action-label="Choose or change boss"
      :expanded="false"
      @activate="editor.setMode('boss')"
    />
    <div class="theme-divider flex items-center justify-between border-b px-5 py-3">
      <h4 class="theme-section-title text-sm font-semibold">
        Deck cards
      </h4>
      <span class="theme-section-muted text-xs">{{ editor.form.entries.length }} unique</span>
    </div>
    <div
      ref="scrollRef"
      class="app-scrollbar relative mt-4 min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pb-5 pr-4"
    >
      <div
        ref="listRef"
        class="space-y-3 pb-1"
      >
        <div
          v-if="!editor.form.entries.length"
          class="theme-empty-state"
        >
          No cards added to this Encounter yet.
        </div>
        <template
          v-for="entry in editor.form.entries"
          :key="entry.card_id"
        >
          <CardBuilderEntryRow
            v-if="editor.cards.value[entry.card_id]"
            :entry="{ card: editor.cards.value[entry.card_id], quantity: entry.quantity }"
            :sortable-card-id="entry.card_id"
            :hover-mode="hoverMode"
            :move-destinations="[]"
            :mutation-disabled="editor.locked.value"
            :row-action-disabled="editor.locked.value"
            :row-secondary-action-disabled="editor.locked.value"
            @increment="editor.quantity(entry.card_id, entry.quantity + 1)"
            @decrement="editor.quantity(entry.card_id, entry.quantity - 1)"
            @remove="editor.quantity(entry.card_id, 0)"
            @row-action="editor.quantity(entry.card_id, entry.quantity + 1)"
            @row-secondary-action="editor.quantity(entry.card_id, entry.quantity - 1)"
          />
          <p
            v-else
            class="theme-error-text text-sm"
          >
            Card unavailable: {{ entry.card_id }}
          </p>
        </template>
      </div>
    </div>
  </aside>
</template>
<script setup lang="ts">
import { ref, shallowRef, watch } from 'vue';
import { useSortable } from '@vueuse/integrations/useSortable';
import CardBuilderEntryRow from '@/domain/cards/components/CardBuilderEntryRow.vue';
import CardBuilderSummaryHeader from '@/domain/cards/components/CardBuilderSummaryHeader.vue';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';
import type { useEncounterEditor } from '../composables/useEncounterEditor';
const props = defineProps<{
  editor: ReturnType<typeof useEncounterEditor>;
  hoverMode: HoverMode;
}>();
const listRef = ref<HTMLElement | null>(null);
const scrollRef = ref<HTMLElement | null>(null);
const entries = shallowRef([...props.editor.form.entries]);
const sortable = useSortable(listRef, entries, {
  animation: 160,
  handle: '.deck-board-entry-drag-handle',
  watchElement: true,
  scroll: true,
  forceAutoScrollFallback: true,
  bubbleScroll: false,
  scrollSensitivity: 180,
  scrollSpeed: 18,
  onUpdate: (event) => {
    if (props.editor.locked.value || event.newIndex === undefined) return;
    const from = props.editor.form.entries.findIndex(
      (entry) => entry.card_id === event.item.dataset.cardId,
    );
    if (from >= 0) props.editor.move(from, event.newIndex - from);
  },
});
watch(
  () => props.editor.form.entries,
  (value) => {
    entries.value = [...value];
  },
  { deep: true },
);
watch(
  () => props.editor.locked.value,
  (value) => sortable.option('disabled', value),
  { immediate: true },
);
watch(scrollRef, (value) => sortable.option('scroll', value ?? true));
</script>
