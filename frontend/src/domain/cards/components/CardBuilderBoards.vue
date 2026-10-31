<template>
  <div>
    <div class="space-y-3 px-5">
      <div class="space-y-3">
        <div class="flex items-center justify-between gap-3">
          <h4 class="theme-section-title text-sm font-semibold">
            Deck Boards
          </h4>
          <button
            class="btn-secondary inline-flex h-8 shrink-0 items-center gap-1.5 px-3 py-0 text-xs"
            type="button"
            :disabled="locked"
            @click="emit('add')"
          >
            <Plus class="h-3.5 w-3.5" />
            Add Sideboard
          </button>
        </div>

        <div
          v-if="sideboards.length > 0"
          class="flex min-h-8 flex-wrap items-center gap-2"
        >
          <button
            class="theme-pill text-xs"
            :class="activeBoardId === 'mainboard' ? 'theme-pill-accent' : 'theme-pill-neutral'"
            type="button"
            :disabled="locked"
            @click="emit('select', 'mainboard')"
          >
            Mainboard ({{ mainboardCount }})
          </button>
          <div
            v-for="sideboard in sideboards"
            :key="sideboard.id"
            class="inline-flex items-center"
            @mouseenter="hoveredSideboardId = sideboard.id"
            @mouseleave="clearHoveredSideboard(sideboard.id)"
            @focusin="focusedSideboardId = sideboard.id"
            @focusout="handleSideboardFocusOut($event, sideboard.id)"
          >
            <button
              v-if="editingSideboardId !== sideboard.id"
              class="theme-pill text-xs"
              :class="activeBoardId === sideboard.id ? 'theme-pill-accent' : 'theme-pill-neutral'"
              type="button"
              @click="selectSideboard(sideboard.id)"
            >
              <span class="truncate"> {{ sideboard.name }} ({{ sideboard.totalCards }}) </span>
            </button>
            <div
              v-else
              class="theme-pill theme-pill-accent inline-flex items-center px-2 py-1"
            >
              <input
                :ref="setEditingSideboardInputRef"
                v-model="editingSideboardName"
                class="min-w-[7rem] bg-transparent text-xs font-medium outline-none"
                :aria-label="`Rename ${sideboard.name}`"
                @click.stop
                @keydown.enter.prevent="commitRenameSideboard()"
                @keydown.esc.prevent="cancelRenameSideboard()"
                @blur="commitRenameSideboard()"
              >
            </div>

            <button
              class="theme-card-frame-muted theme-section-title -ml-2 inline-flex h-7 w-7 items-center justify-center rounded-full"
              :class="shouldShowSideboardActions(sideboard.id) ? '' : 'invisible pointer-events-none'"
              type="button"
              :aria-label="`Open sideboard actions for ${sideboard.name}`"
              :aria-hidden="!shouldShowSideboardActions(sideboard.id)"
              :tabindex="shouldShowSideboardActions(sideboard.id) ? 0 : -1"
              @click="openSideboardActions($event, sideboard.id)"
            >
              <Ellipsis class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
    <Teleport to="body">
      <div
        v-if="sideboardActionsOpen && sideboardActionsTargetId && !locked"
        ref="sideboardActionsPanelRef"
        class="theme-popover z-40 w-44 p-2"
        :style="{
          position: 'fixed',
          left: `${sideboardActionsX}px`,
          top: `${sideboardActionsY}px`,
        }"
      >
        <div class="space-y-1">
          <button
            type="button"
            class="btn-secondary w-full justify-start gap-2 px-3 py-2 text-xs"
            :disabled="locked"
            @click="
              beginRenameSideboard(
                sideboardActionsTargetId,
                sideboards.find((sideboard) => sideboard.id === sideboardActionsTargetId)?.name ?? '',
              )
            "
          >
            <Pencil class="h-3.5 w-3.5" />
            Rename
          </button>
          <button
            type="button"
            class="btn-danger-secondary w-full justify-start gap-2 px-3 py-2 text-xs"
            :disabled="locked"
            @click="
              promptDeleteSideboard(
                sideboardActionsTargetId,
                sideboards.find((sideboard) => sideboard.id === sideboardActionsTargetId)?.name ??
                  'sideboard',
              )
            "
          >
            <Trash2 class="h-3.5 w-3.5" />
            Delete
          </button>
        </div>
      </div>
    </Teleport>

    <ConfirmModal
      :open="deleteSideboardTarget !== null"
      title="Delete Sideboard"
      :message="deleteSideboardTarget ? `Delete sideboard '${deleteSideboardTarget.name}'?` : ''"
      confirm-label="Delete"
      cancel-label="Cancel"
      @cancel="deleteSideboardTarget = null"
      @confirm="confirmDeleteSideboard"
    />
  </div>
</template>
<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';
import { Ellipsis, Pencil, Plus, Trash2 } from 'lucide-vue-next';
import { useFloatingPopover } from '@/shared/composables/useFloatingPopover';
import ConfirmModal from '@/shared/components/modals/ConfirmModal.vue';
const props = defineProps<{
  activeBoardId: string;
  mainboardCount: number;
  sideboards: Array<{ id: string; name: string; totalCards: number }>;
  locked: boolean;
}>();
const emit = defineEmits<{
  add: [];
  select: [id: string];
  rename: [id: string, name: string];
  remove: [id: string];
}>();
const {
  isOpen: sideboardActionsOpen,
  triggerRef: sideboardActionsTriggerRef,
  panelRef: sideboardActionsPanelRef,
  x: sideboardActionsX,
  y: sideboardActionsY,
  toggle: toggleSideboardActions,
  close: closeSideboardActions,
} = useFloatingPopover({
  placement: 'bottom-end',
});
const sideboardActionsTargetId = ref<string | null>(null);
const editingSideboardId = ref<string | null>(null);
const editingSideboardName = ref('');
const editingSideboardInputRef = ref<HTMLInputElement | null>(null);
const deleteSideboardTarget = ref<{ id: string; name: string } | null>(null);
const hoveredSideboardId = ref<string | null>(null);
const focusedSideboardId = ref<string | null>(null);
const selectSideboard = (sideboardId: string): void => {
  if (props.locked || editingSideboardId.value === sideboardId) {
    return;
  }
  emit('select', sideboardId);
};

const setEditingSideboardInputRef = (element: unknown): void => {
  editingSideboardInputRef.value = element instanceof HTMLInputElement ? element : null;
};

const openSideboardActions = (event: MouseEvent, sideboardId: string): void => {
  event.stopPropagation();
  if (props.locked) {
    return;
  }
  sideboardActionsTriggerRef.value = event.currentTarget as HTMLElement | null;
  if (sideboardActionsOpen.value && sideboardActionsTargetId.value === sideboardId) {
    closeSideboardActions();
    sideboardActionsTargetId.value = null;
    return;
  }

  sideboardActionsTargetId.value = sideboardId;
  if (sideboardActionsOpen.value) {
    closeSideboardActions();
  }
  toggleSideboardActions();
};

const clearHoveredSideboard = (sideboardId: string): void => {
  if (hoveredSideboardId.value === sideboardId) {
    hoveredSideboardId.value = null;
  }
};

const handleSideboardFocusOut = (event: FocusEvent, sideboardId: string): void => {
  const currentTarget = event.currentTarget;
  if (!(currentTarget instanceof HTMLElement)) {
    return;
  }
  const nextTarget = event.relatedTarget as Node | null;
  if (nextTarget && currentTarget.contains(nextTarget)) {
    return;
  }
  if (focusedSideboardId.value === sideboardId) {
    focusedSideboardId.value = null;
  }
};

const shouldShowSideboardActions = (sideboardId: string): boolean => {
  if (editingSideboardId.value === sideboardId) {
    return false;
  }
  if (sideboardActionsOpen.value && sideboardActionsTargetId.value === sideboardId) {
    return true;
  }
  return hoveredSideboardId.value === sideboardId || focusedSideboardId.value === sideboardId;
};

const beginRenameSideboard = async (sideboardId: string, name: string): Promise<void> => {
  if (props.locked) {
    return;
  }
  closeSideboardActions();
  sideboardActionsTargetId.value = null;
  editingSideboardId.value = sideboardId;
  editingSideboardName.value = name;
  await nextTick();
  editingSideboardInputRef.value?.focus();
  editingSideboardInputRef.value?.select();
};

const cancelRenameSideboard = (): void => {
  editingSideboardId.value = null;
  editingSideboardName.value = '';
};

const commitRenameSideboard = (): void => {
  if (props.locked || !editingSideboardId.value) {
    return;
  }
  const nextName = editingSideboardName.value.trim();
  if (!nextName) {
    cancelRenameSideboard();
    return;
  }

  emit('rename', editingSideboardId.value, nextName);
  cancelRenameSideboard();
};

const promptDeleteSideboard = (sideboardId: string, name: string): void => {
  if (props.locked) {
    return;
  }
  closeSideboardActions();
  sideboardActionsTargetId.value = null;
  deleteSideboardTarget.value = { id: sideboardId, name };
};

const confirmDeleteSideboard = (): void => {
  if (props.locked || !deleteSideboardTarget.value) {
    return;
  }
  if (props.activeBoardId === deleteSideboardTarget.value.id) {
    emit('select', 'mainboard');
  }
  emit('remove', deleteSideboardTarget.value.id);
  deleteSideboardTarget.value = null;
};

watch(
  () => props.locked,
  (locked) => {
    if (!locked) return;
    closeSideboardActions();
    sideboardActionsTargetId.value = null;
    deleteSideboardTarget.value = null;
    cancelRenameSideboard();
  },
);
</script>
