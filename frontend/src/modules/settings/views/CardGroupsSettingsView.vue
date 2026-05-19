<template>
  <div class="page-card flex min-h-0 flex-col space-y-4 xl:h-[calc(100vh-10rem)]">
    <div class="flex items-center justify-between gap-3">
      <div>
        <h3 class="text-base font-semibold text-slate-800">
          Card groups
        </h3>
        <p class="text-sm text-slate-500">
          Group anchored cards together for gallery presentation and detail browsing.
        </p>
      </div>
      <button
        class="btn-primary"
        type="button"
        @click="startCreate"
      >
        New group
      </button>
    </div>

    <div class="grid min-h-0 flex-1 gap-4 xl:grid-cols-[280px_320px_minmax(0,1fr)]">
      <aside class="min-h-0 space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <input
          v-model="listSearch"
          class="input-base"
          placeholder="Search card groups..."
        >
        <div class="app-scrollbar space-y-2 overflow-y-auto xl:h-[calc(100vh-17rem)]">
          <button
            v-for="group in filteredGroups"
            :key="group.id"
            type="button"
            class="w-full rounded-xl border p-3 text-left transition"
            :class="selectedGroupId === group.id ? 'border-sky-300 bg-white shadow-sm' : 'border-slate-200 bg-white hover:border-slate-300'"
            @click="selectGroup(group.id)"
          >
            <p class="text-sm font-semibold text-slate-900">
              {{ group.name }}
            </p>
            <p class="mt-1 text-xs text-slate-500">
              {{ group.member_count }} cards · Anchor: {{ group.anchor_card_name }}
            </p>
          </button>
        </div>
      </aside>

      <section class="min-h-0 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div class="space-y-3">
          <div>
            <h4 class="text-sm font-semibold text-slate-900">
              Card search
            </h4>
            <p class="text-xs text-slate-500">
              Find cards to add to the selected group.
            </p>
          </div>

          <div class="flex gap-2">
            <input
              v-model="pickerQuery"
              class="input-base"
              placeholder="Search cards to add..."
              @keydown.enter.prevent
            >
          </div>

          <div class="app-scrollbar space-y-2 overflow-y-auto xl:h-[calc(100vh-20rem)]">
            <div
              v-if="pickerResults.length === 0"
              class="rounded-xl border border-dashed border-slate-300 bg-white px-3 py-4 text-sm text-slate-500"
            >
              Search for cards to add them here.
            </div>
            <button
              v-for="result in pickerResults"
              :key="result.id"
              type="button"
              class="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2 text-left transition hover:border-slate-300"
              :disabled="memberIds.has(result.id)"
              @click="addMember(result)"
            >
              <div>
                <p class="text-sm font-medium text-slate-900">
                  {{ result.name }}
                </p>
                <p class="text-xs text-slate-500">
                  {{ result.label }}
                </p>
              </div>
              <span class="text-xs font-semibold text-sky-700">
                {{ memberIds.has(result.id) ? 'Added' : 'Add' }}
              </span>
            </button>
          </div>
        </div>
      </section>

      <section class="min-h-0 rounded-2xl border border-slate-200 bg-white p-4">
        <div
          v-if="editor"
          class="app-scrollbar space-y-5 overflow-y-auto xl:h-[calc(100vh-17rem)]"
        >
          <div class="flex items-center justify-between gap-3">
            <div>
              <h4 class="text-lg font-semibold text-slate-900">
                {{ editor.id ? 'Edit card group' : 'Create card group' }}
              </h4>
              <p class="text-sm text-slate-500">
                Anchor cards are always kept at position 1.
              </p>
            </div>
            <div class="flex gap-2">
              <button
                v-if="editor.id"
                class="btn-secondary"
                type="button"
                @click="openPublicView"
              >
                Open
              </button>
              <button
                v-if="editor.id"
                class="btn-secondary text-rose-700 hover:text-rose-800"
                type="button"
                @click="deleteGroup"
              >
                Delete
              </button>
            </div>
          </div>

          <label class="block space-y-2">
            <span class="text-sm font-semibold text-slate-900">Name</span>
            <input
              v-model="editor.name"
              class="input-base"
              placeholder="Defaults to anchor card name"
            >
          </label>

          <div class="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div class="flex items-center justify-between gap-3">
              <div>
                <h5 class="text-sm font-semibold text-slate-900">
                  Members
                </h5>
                <p class="text-xs text-slate-500">
                  Drag to reorder, or use the anchor selector to choose the stack front.
                </p>
              </div>
              <span class="text-xs font-medium text-slate-500">
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
                class="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3"
                draggable="true"
                @dragstart="onDragStart(index)"
                @dragover.prevent
                @drop="onDrop(index)"
              >
                <div class="h-20 w-16 shrink-0 overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
                  <img
                    v-if="member.image_url"
                    :src="toAbsoluteApiUrl(member.image_url)"
                    :alt="member.card_name"
                    class="h-full w-full object-contain"
                  >
                  <div
                    v-else
                    class="flex h-full items-center justify-center text-[11px] text-slate-400"
                  >
                    No image
                  </div>
                </div>

                <div class="min-w-0 flex-1">
                  <p class="text-sm font-semibold text-slate-900">
                    {{ member.card_name }}
                  </p>
                  <p class="text-xs text-slate-500">
                    Position {{ index + 1 }}
                  </p>
                </div>

                <label class="flex items-center gap-2 text-xs font-medium text-slate-600">
                  <input
                    :checked="editor.anchor_card_id === member.card_id"
                    type="radio"
                    name="anchor-card"
                    class="h-4 w-4 border-slate-300 text-sky-600"
                    @change="setAnchor(member.card_id)"
                  >
                  <span>Anchor</span>
                </label>

                <button
                  class="rounded-lg px-2 py-1 text-xs font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
                  type="button"
                  @click="moveMember(index, -1)"
                >
                  Up
                </button>
                <button
                  class="rounded-lg px-2 py-1 text-xs font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
                  type="button"
                  @click="moveMember(index, 1)"
                >
                  Down
                </button>
                <button
                  class="rounded-lg px-2 py-1 text-xs font-semibold text-rose-700 transition hover:bg-rose-50"
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
              class="text-sm text-slate-500"
            >
              Add at least two cards to create a card group.
            </p>
          </div>

          <p
            v-if="errorMessage"
            class="text-sm text-rose-700"
          >
            {{ errorMessage }}
          </p>

          <div class="flex gap-2">
            <button
              class="btn-primary"
              type="button"
              @click="saveGroup"
            >
              {{ editor.id ? 'Save changes' : 'Create group' }}
            </button>
            <button
              class="btn-secondary"
              type="button"
              @click="resetEditor"
            >
              Reset
            </button>
          </div>
        </div>

        <div
          v-else
          class="flex h-full items-center justify-center text-sm text-slate-500"
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
import { api, toAbsoluteApiUrl } from '@/api/client';
import type { CardListItem, PaginatedCardsResponse } from '@/modules/card-detail/types';
import type { CardGroupMemberRecord, CardGroupRecord } from '@/modules/settings/types';

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
  const response = await api.get<CardGroupRecord[]>('/settings/card-groups');
  groups.value = response.data;
  if (selectedGroupId.value) {
    const next = groups.value.find((group) => group.id === selectedGroupId.value);
    if (next) {
      applyEditor(next);
    }
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
    return null;
  }
  if (!editor.value.anchor_card_id) {
    errorMessage.value = 'Choose an anchor card before saving.';
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
      const response = await api.patch<CardGroupRecord>(`/settings/card-groups/${editor.value.id}`, payload);
      savedGroup = response.data;
    } else {
      const response = await api.post<CardGroupRecord>('/settings/card-groups', payload);
      savedGroup = response.data;
    }
    await loadGroups();
    const next = groups.value.find((group) => group.id === savedGroup.id);
    if (next) {
      applyEditor(next);
    }
  } catch (error) {
    console.error(error);
    errorMessage.value = 'Unable to save card group.';
  }
};

const deleteGroup = async (): Promise<void> => {
  if (!editor.value?.id) {
    return;
  }
  await api.delete(`/settings/card-groups/${editor.value.id}`);
  startCreate();
  await loadGroups();
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
</script>
