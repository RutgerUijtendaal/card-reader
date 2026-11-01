<template>
  <aside
    class="app-sticky-aside app-sticky-aside-right page-card flex min-h-0 flex-col overflow-hidden p-0"
  >
    <CardBuilderSummaryHeader
      :name="editor.form.name || 'Untitled Encounter'"
      :card="editor.boss.value"
      :board-label="editor.boards.getBoardLabel(editor.boards.activeBoardId.value)"
      :count="
        editor.boards.activeBoardEntries.value.reduce((sum, entry) => sum + entry.quantity, 0)
      "
      empty-label="Choose boss"
      action-label="Choose or change boss"
      :expanded="false"
      @activate="editor.setMode('boss')"
    />
    <BuilderPanelTabs
      label="Encounter builder view"
      :tabs="viewTabs"
      :disabled="editor.locked.value"
      @select="selectView"
    />
    <div
      v-if="editor.boss.value"
      class="flex justify-end px-5 pt-2"
    >
      <button
        class="theme-ghost-button inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium"
        type="button"
        :disabled="editor.locked.value"
        @click="editor.selectBoss(null)"
      >
        Clear boss
      </button>
    </div>
    <CardBuilderBoards
      class="mt-2"
      :active-board-id="editor.boards.activeBoardId.value"
      :mainboard-count="editor.total.value"
      :sideboards="editor.boards.sideboardTabs.value"
      :locked="editor.locked.value"
      @add="editor.addSideboard"
      @select="editor.boards.selectBoard"
      @rename="editor.renameSideboard"
      @remove="editor.removeSideboard"
    />
    <div
      ref="scrollRef"
      class="app-scrollbar relative mt-4 min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pb-5 pr-4"
    >
      <div
        ref="listRef"
        class="space-y-3 pb-1"
      >
        <div
          v-if="!editor.boards.activeBoardEntries.value.length"
          class="theme-empty-state"
        >
          No cards added to this board yet.
        </div>
        <template
          v-for="entry in editor.boards.activeBoardEntries.value"
          :key="entry.card_id"
        >
          <CardBuilderEntryRow
            v-if="editor.cards.value[entry.card_id]"
            :entry="{ card: editor.cards.value[entry.card_id], quantity: entry.quantity }"
            :sortable-card-id="entry.card_id"
            :hover-mode="hoverMode"
            :move-destinations="destinations"
            :mutation-disabled="editor.locked.value"
            :row-action-disabled="editor.locked.value"
            :row-secondary-action-disabled="editor.locked.value"
            @move-to-board="editor.moveToBoard"
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
import { computed, ref, shallowRef, watch } from 'vue';
import { useSortable } from '@vueuse/integrations/useSortable';
import { Crown, FileText, LayoutGrid } from 'lucide-vue-next';
import BuilderPanelTabs from '@/shared/components/builders/BuilderPanelTabs.vue';
import CardBuilderBoards from '@/domain/cards/components/CardBuilderBoards.vue';
import CardBuilderEntryRow from '@/domain/cards/components/CardBuilderEntryRow.vue';
import CardBuilderSummaryHeader from '@/domain/cards/components/CardBuilderSummaryHeader.vue';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';
import type { useEncounterEditor } from '../composables/useEncounterEditor';
const props = defineProps<{
  editor: ReturnType<typeof useEncounterEditor>;
  hoverMode: HoverMode;
}>();
type EncounterBuilderView = 'cards' | 'boss' | 'details';
const viewTabs = computed(() => {
  const detailsOpen = props.editor.detailsOpen.value;
  const mode = props.editor.mode.value;
  return [
    { id: 'boss' as const, label: 'Boss', icon: Crown, active: !detailsOpen && mode === 'boss' },
    { id: 'cards' as const, label: 'Cards', icon: LayoutGrid, active: !detailsOpen && mode === 'cards' },
    { id: 'details' as const, label: 'Details', icon: FileText, active: detailsOpen },
  ];
});
const selectView = (view: EncounterBuilderView): void => {
  if (view === 'details') props.editor.openDetails();
  else props.editor.setMode(view);
};
const destinations = computed(() =>
  [
    { boardId: 'mainboard', label: 'Mainboard', disabled: false },
    ...props.editor.boards.sideboardTabs.value.map((board) => ({
      boardId: board.id,
      label: board.name,
      disabled: false,
    })),
  ].filter((board) => board.boardId !== props.editor.boards.activeBoardId.value),
);
const listRef = ref<HTMLElement | null>(null);
const scrollRef = ref<HTMLElement | null>(null);
const entries = shallowRef([...props.editor.boards.activeBoardEntries.value]);
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
    const from = props.editor.boards.activeBoardEntries.value.findIndex(
      (entry) => entry.card_id === event.item.dataset.cardId,
    );
    if (from >= 0) props.editor.move(from, event.newIndex - from);
  },
});
watch(
  () => props.editor.boards.activeBoardEntries.value,
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
