<template>
  <div class="page-card flex min-h-0 flex-col space-y-4 xl:h-[calc(100vh-10rem)]">
    <div>
      <h3 class="theme-section-title text-base font-semibold">
        Card groups
      </h3>
      <p class="theme-section-muted text-sm">
        Group anchored cards together for gallery presentation and detail browsing.
      </p>
    </div>

    <div class="grid min-h-0 flex-1 gap-4 xl:grid-cols-[280px_320px_minmax(0,1fr)]">
      <aside class="theme-panel-shell flex min-h-0 flex-col p-4">
        <div class="theme-divider flex flex-col gap-3 border-b pb-4">
          <div class="flex items-start justify-between gap-3">
            <div>
              <h4 class="theme-section-title text-sm font-semibold">
                Card groups
              </h4>
              <p class="theme-section-muted mt-1 text-xs">
                {{ filteredGroups.length }} of {{ groups.length }} shown
              </p>
            </div>
            <button
              class="btn-secondary px-3 py-2 text-xs"
              type="button"
              @click="startCreate"
            >
              New Group
            </button>
          </div>

          <label class="block">
            <span class="theme-kicker mb-1 block text-xs font-medium uppercase tracking-[0.16em]">
              Filter groups
            </span>
            <input
              v-model="listSearch"
              class="input-base"
              placeholder="Search card groups..."
            >
          </label>
        </div>

        <div class="app-scrollbar mt-4 min-h-0 space-y-2 overflow-y-auto pr-1 xl:h-[calc(100vh-17rem)]">
          <button
            v-for="group in filteredGroups"
            :key="group.id"
            type="button"
            class="w-full rounded-xl border p-3 text-left transition"
            :class="selectedGroupId === group.id ? 'theme-selected-surface-strong' : 'theme-card-frame hover:-translate-y-0.5'"
            @click="selectGroup(group.id)"
          >
            <div class="flex items-start justify-between gap-3">
              <p class="theme-section-title text-sm font-semibold">
                {{ group.name }}
              </p>
              <span class="theme-pill theme-pill-accent text-nowrap">
                {{ group.member_count }}
              </span>
            </div>
            <p class="theme-section-muted mt-1 text-xs">
              Anchor: {{ group.anchor_card_name }}
            </p>
          </button>
        </div>
      </aside>

      <section class="theme-panel-shell flex min-h-0 flex-col p-4">
        <div class="theme-divider flex flex-col gap-3 border-b pb-4">
          <div>
            <h4 class="theme-section-title text-sm font-semibold">
              Card search
            </h4>
            <p class="theme-section-muted mt-1 text-xs">
              Find cards to add to the selected group.
            </p>
          </div>

          <label class="block">
            <span class="theme-kicker mb-1 block text-xs font-medium uppercase tracking-[0.16em]">
              Search cards
            </span>
            <input
              v-model="pickerQuery"
              class="input-base"
              placeholder="Search cards to add..."
              @keydown.enter.prevent
            >
          </label>
        </div>

        <div class="app-scrollbar mt-4 min-h-0 space-y-2 overflow-y-auto pr-1 xl:h-[calc(100vh-20rem)]">
          <div
            v-if="pickerResults.length === 0"
            class="theme-empty-state"
          >
            Search for cards to add them here.
          </div>
          <button
            v-for="result in pickerResults"
            :key="result.id"
            type="button"
            class="theme-selected-surface flex w-full items-center justify-between rounded-xl px-3 py-2 text-left transition hover:-translate-y-0.5"
            :disabled="memberIds.has(result.id)"
            @click="addMember(result)"
          >
            <div>
              <p class="theme-section-title text-sm font-medium">
                {{ result.name }}
              </p>
              <p class="theme-section-muted text-xs">
                {{ result.label }}
              </p>
            </div>
            <span class="theme-link text-xs font-semibold">
              {{ memberIds.has(result.id) ? 'Added' : 'Add' }}
            </span>
          </button>
        </div>
      </section>

      <section class="theme-panel-shell flex min-h-0 flex-col p-4">
        <template v-if="editor">
          <div
            class="app-scrollbar min-h-0 flex-1 space-y-5 overflow-y-auto pr-1 xl:h-[calc(100vh-17rem)]"
          >
            <div class="flex items-center justify-between gap-3">
              <div>
                <h4 class="theme-section-title text-lg font-semibold">
                  {{ editor.id ? 'Edit card group' : 'Create card group' }}
                </h4>
                <p class="theme-section-muted text-sm">
                  Anchor cards are always kept at position 1.
                </p>
              </div>
            </div>

            <label class="block space-y-2">
              <span class="theme-section-title text-sm font-semibold">Name</span>
              <input
                v-model="editor.name"
                class="input-base"
                placeholder="Defaults to anchor card name"
              >
            </label>

            <div class="theme-muted-panel space-y-3">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <h5 class="theme-section-title text-sm font-semibold">
                    Members
                  </h5>
                  <p class="theme-section-muted text-xs">
                    Drag to reorder, or use the anchor selector to choose the stack front.
                  </p>
                </div>
                <span class="theme-section-muted text-xs font-medium">
                  {{ editor.members.length }} cards
                </span>
              </div>

              <div
                v-if="editor.members.length > 0"
                class="space-y-2"
              >
                <div
                  v-for="(member, index) in editor.members"
                  :key="member.card_id"
                  class="theme-card-frame flex items-center gap-3 rounded-xl p-3"
                  draggable="true"
                  @dragstart="onDragStart(index)"
                  @dragover.prevent
                  @drop="onDrop(index)"
                >
                  <div class="theme-card-frame-muted theme-card-image-well h-20 w-16 shrink-0 rounded-lg">
                    <img
                      v-if="member.image_url"
                      :src="toAbsoluteApiUrl(member.image_url)"
                      :alt="member.card_name"
                      class="h-full w-full object-contain"
                    >
                    <div
                      v-else
                      class="theme-kicker flex h-full items-center justify-center text-[11px]"
                    >
                      No image
                    </div>
                  </div>

                  <div class="min-w-0 flex-1">
                    <p class="theme-section-title text-sm font-semibold">
                      {{ member.card_name }}
                    </p>
                    <p class="theme-section-muted text-xs">
                      Position {{ index + 1 }}
                    </p>
                  </div>

                  <label class="theme-section-muted flex items-center gap-2 text-xs font-medium">
                    <input
                      :checked="editor.anchor_card_id === member.card_id"
                      type="radio"
                      name="anchor-card"
                      class="theme-checkbox h-4 w-4 border-slate-300"
                      @change="setAnchor(member.card_id)"
                    >
                    <span>Anchor</span>
                  </label>

                  <button
                    class="btn-secondary px-2 py-1 text-xs font-semibold"
                    type="button"
                    @click="moveMember(index, -1)"
                  >
                    Up
                  </button>
                  <button
                    class="btn-secondary px-2 py-1 text-xs font-semibold"
                    type="button"
                    @click="moveMember(index, 1)"
                  >
                    Down
                  </button>
                  <button
                    class="btn-danger-secondary rounded-lg px-2 py-1 text-xs font-semibold"
                    type="button"
                    :disabled="editor.anchor_card_id === member.card_id"
                    @click="removeMember(member.card_id)"
                  >
                    Remove
                  </button>
                </div>
              </div>

              <p
                v-else
                class="theme-section-muted text-sm"
              >
                Add at least two cards to create a card group.
              </p>
            </div>

            <p
              v-if="errorMessage"
              class="theme-error-text text-sm"
            >
              {{ errorMessage }}
            </p>
          </div>

          <div class="theme-divider mt-5 flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
              <button
                v-if="editor.id"
                class="btn-secondary"
                type="button"
                @click="openPublicView"
              >
                Open
              </button>
              <button
                class="btn-secondary"
                type="button"
                @click="resetEditor"
              >
                Reset
              </button>
            </div>

            <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
              <button
                v-if="editor.id"
                class="btn-danger-secondary"
                type="button"
                @click="deleteGroup"
              >
                Delete
              </button>
              <button
                class="btn-primary"
                type="button"
                @click="saveGroup"
              >
                {{ editor.id ? 'Save Changes' : 'Create Group' }}
              </button>
            </div>
          </div>
        </template>

        <div
          v-else
          class="theme-section-muted flex h-full items-center justify-center text-sm"
        >
          Select a card group or create a new one.
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDebounceFn } from '@vueuse/core';
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { toast } from 'vue-sonner';
import { api, toAbsoluteApiUrl } from '@/api/client';
import type { CardListItem, PaginatedCardsResponse } from '@/modules/card-detail/types';
import type { CardGroupMemberRecord, CardGroupRecord } from '@/modules/admin/types';

type CardGroupEditor = {
  id: string | null;
  name: string;
  anchor_card_id: string;
  members: CardGroupMemberRecord[];
};

const router = useRouter();
const groups = ref<CardGroupRecord[]>([]);
const selectedGroupId = ref<string | null>(null);
const editor = ref<CardGroupEditor | null>(null);
const listSearch = ref('');
const pickerQuery = ref('');
const pickerResults = ref<CardListItem[]>([]);
const errorMessage = ref('');
const dragIndex = ref<number | null>(null);

const filteredGroups = computed(() => {
  const query = listSearch.value.trim().toLowerCase();
  if (!query) {
    return groups.value;
  }
  return groups.value.filter((group) =>
    [group.name, group.anchor_card_name].some((value) => value.toLowerCase().includes(query)),
  );
});

const memberIds = computed(() => new Set(editor.value?.members.map((member) => member.card_id) ?? []));

const loadGroups = async (): Promise<void> => {
  try {
    const response = await api.get<CardGroupRecord[]>('/admin/card-groups');
    groups.value = response.data;
    if (selectedGroupId.value) {
      const next = groups.value.find((group) => group.id === selectedGroupId.value);
      if (next) {
        applyEditor(next);
      }
    }
  } catch (error) {
    console.error('Load card groups failed', error);
    toast.error(extractErrorMessage(error, 'Failed to load card groups.'));
  }
};

const applyEditor = (group: CardGroupRecord): void => {
  selectedGroupId.value = group.id;
  editor.value = {
    id: group.id,
    name: group.name,
    anchor_card_id: group.anchor_card_id,
    members: group.members.map((member) => ({ ...member })),
  };
  normalizeEditor();
  errorMessage.value = '';
};

const selectGroup = (groupId: string): void => {
  const group = groups.value.find((row) => row.id === groupId);
  if (!group) {
    return;
  }
  applyEditor(group);
};

const startCreate = (): void => {
  selectedGroupId.value = null;
  editor.value = {
    id: null,
    name: '',
    anchor_card_id: '',
    members: [],
  };
  pickerResults.value = [];
  errorMessage.value = '';
};

const resetEditor = (): void => {
  if (!editor.value) {
    return;
  }
  if (editor.value.id) {
    selectGroup(editor.value.id);
    return;
  }
  startCreate();
};

const searchCards = async (): Promise<void> => {
  const query = pickerQuery.value.trim();
  if (!query) {
    pickerResults.value = [];
    return;
  }
  const response = await api.get<PaginatedCardsResponse<CardListItem>>('/cards', {
    params: {
      q: query,
      page_size: 10,
    },
  });
  pickerResults.value = response.data.results.filter((row) => row.result_type === 'card');
};

const debouncedSearchCards = useDebounceFn(() => {
  void searchCards();
}, 250);

const addMember = (card: CardListItem): void => {
  if (!editor.value || memberIds.value.has(card.id)) {
    return;
  }
  editor.value.members.push({
    card_id: card.id,
    card_label: card.label,
    card_name: card.name,
    position: editor.value.members.length + 1,
    is_anchor: editor.value.anchor_card_id === card.id,
    image_url: card.image_url,
  });
  if (!editor.value.anchor_card_id) {
    editor.value.anchor_card_id = card.id;
  }
  normalizeEditor();
};

const setAnchor = (cardId: string): void => {
  if (!editor.value) {
    return;
  }
  editor.value.anchor_card_id = cardId;
  normalizeEditor();
};

const moveMember = (index: number, direction: -1 | 1): void => {
  if (!editor.value) {
    return;
  }
  const nextIndex = index + direction;
  if (nextIndex < 0 || nextIndex >= editor.value.members.length) {
    return;
  }
  const nextMembers = [...editor.value.members];
  const [moved] = nextMembers.splice(index, 1);
  nextMembers.splice(nextIndex, 0, moved);
  editor.value.members = nextMembers;
  normalizeEditor();
};

const removeMember = (cardId: string): void => {
  if (!editor.value || editor.value.anchor_card_id === cardId) {
    return;
  }
  editor.value.members = editor.value.members.filter((member) => member.card_id !== cardId);
  normalizeEditor();
};

const normalizeEditor = (): void => {
  if (!editor.value) {
    return;
  }
  const anchorId = editor.value.anchor_card_id;
  const anchorMember = editor.value.members.find((member) => member.card_id === anchorId) ?? null;
  const otherMembers = editor.value.members.filter((member) => member.card_id !== anchorId);
  const orderedMembers = anchorMember ? [anchorMember, ...otherMembers] : otherMembers;
  editor.value.members = orderedMembers.map((member, index) => ({
    ...member,
    position: index + 1,
    is_anchor: member.card_id === editor.value?.anchor_card_id,
  }));
};

const buildPayload = (): Record<string, unknown> | null => {
  if (!editor.value) {
    return null;
  }
  if (editor.value.members.length < 2) {
    errorMessage.value = 'Card groups require at least 2 cards.';
    toast.error(errorMessage.value);
    return null;
  }
  if (!editor.value.anchor_card_id) {
    errorMessage.value = 'Choose an anchor card before saving.';
    toast.error(errorMessage.value);
    return null;
  }
  errorMessage.value = '';
  return {
    name: editor.value.name,
    anchor_card_id: editor.value.anchor_card_id,
    members: editor.value.members.map((member, index) => ({
      card_id: member.card_id,
      position: index + 1,
    })),
  };
};

const saveGroup = async (): Promise<void> => {
  const payload = buildPayload();
  if (!payload || !editor.value) {
    return;
  }
  try {
    let savedGroup: CardGroupRecord;
    if (editor.value.id) {
      const response = await api.patch<CardGroupRecord>(`/admin/card-groups/${editor.value.id}`, payload);
      savedGroup = response.data;
      toast.success('Card group updated.');
    } else {
      const response = await api.post<CardGroupRecord>('/admin/card-groups', payload);
      savedGroup = response.data;
      toast.success('Card group created.');
    }
    await loadGroups();
    const next = groups.value.find((group) => group.id === savedGroup.id);
    if (next) {
      applyEditor(next);
    }
  } catch (error) {
    console.error('Save card group failed', error);
    errorMessage.value = extractErrorMessage(error, 'Unable to save card group.');
    toast.error(errorMessage.value);
  }
};

const deleteGroup = async (): Promise<void> => {
  if (!editor.value?.id) {
    return;
  }
  try {
    await api.delete(`/admin/card-groups/${editor.value.id}`);
    toast.success('Card group deleted.');
    startCreate();
    await loadGroups();
  } catch (error) {
    console.error('Delete card group failed', error);
    toast.error(extractErrorMessage(error, 'Failed to delete card group.'));
  }
};

const openPublicView = (): void => {
  if (!editor.value?.id) {
    return;
  }
  void router.push(`/card-groups/${editor.value.id}`);
};

const onDragStart = (index: number): void => {
  dragIndex.value = index;
};

const onDrop = (index: number): void => {
  if (dragIndex.value === null || !editor.value || dragIndex.value === index) {
    dragIndex.value = null;
    return;
  }
  const nextMembers = [...editor.value.members];
  const [moved] = nextMembers.splice(dragIndex.value, 1);
  nextMembers.splice(index, 0, moved);
  editor.value.members = nextMembers;
  dragIndex.value = null;
  normalizeEditor();
};

onMounted(() => {
  void loadGroups();
});

watch(
  pickerQuery,
  () => {
    debouncedSearchCards();
  },
);

const extractErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const maybeResponse = (error as { response?: { data?: { detail?: unknown } } }).response;
    const detail = maybeResponse?.data?.detail;
    if (typeof detail === 'string' && detail.length > 0) {
      return detail;
    }
  }
  if (typeof error === 'object' && error && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return fallback;
};
</script>
