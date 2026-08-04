<template>
  <AppModal
    :open="open"
    aria-labelledby="mana-type-groups-title"
    panel-class="theme-popover app-scrollbar max-h-[90vh] w-full max-w-3xl overflow-y-auto p-5 shadow-xl"
    @close="requestClose"
  >
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <h2
          id="mana-type-groups-title"
          class="theme-section-title text-lg font-semibold"
        >
          Manage mana groups
        </h2>
        <p class="theme-section-muted mt-1 text-sm">
          Build reusable groups with at least two included or excluded card types.
        </p>
      </div>
      <button
        class="theme-icon-button"
        type="button"
        aria-label="Close mana group manager"
        @click="requestClose"
      >
        <X class="h-4 w-4" />
      </button>
    </div>

    <div class="mt-5 space-y-4">
      <div
        v-if="draftGroups.length === 0"
        class="theme-empty-state"
      >
        No custom groups yet. Add one to compare mana costs across related card types.
      </div>

      <section
        v-for="(group, index) in draftGroups"
        :key="group.id"
        class="theme-divider space-y-3 border-b pb-4 last:border-b-0"
        :data-testid="`mana-type-group-${group.id}`"
      >
        <div
          v-if="!isEditingGroup(group.id)"
          class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
          :data-testid="`mana-type-group-summary-${group.id}`"
        >
          <div class="min-w-0 space-y-2">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="theme-section-title truncate text-sm font-semibold">
                {{ group.name }}
              </h3>
              <span
                class="theme-section-muted inline-flex items-center gap-1 text-[11px]"
                :data-testid="`mana-type-group-visibility-${group.id}`"
              >
                <Eye
                  v-if="group.isVisible"
                  class="h-3 w-3"
                />
                <EyeOff
                  v-else
                  class="h-3 w-3"
                />
                {{ group.isVisible ? 'Shown in statistics' : 'Hidden from statistics' }}
              </span>
            </div>
            <div class="flex flex-wrap gap-1.5">
              <span
                v-for="typeKey in group.typeKeys"
                :key="`include-${typeKey}`"
                class="theme-choice-chip theme-choice-chip-include pointer-events-none px-2 py-0.5 text-[10px]"
              >
                + {{ typeLabel(typeKey) }}
              </span>
              <span
                v-for="typeKey in group.excludedTypeKeys"
                :key="`exclude-${typeKey}`"
                class="theme-choice-chip theme-choice-chip-exclude pointer-events-none px-2 py-0.5 text-[10px]"
              >
                − {{ typeLabel(typeKey) }}
              </span>
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <button
              class="btn-secondary inline-flex h-8 items-center gap-1.5 px-2.5 text-xs"
              type="button"
              :aria-label="`${group.isVisible ? 'Hide' : 'Display'} ${group.name}`"
              @click="toggleGroupVisibility(group)"
            >
              <EyeOff
                v-if="group.isVisible"
                class="h-3.5 w-3.5"
              />
              <Eye
                v-else
                class="h-3.5 w-3.5"
              />
              {{ group.isVisible ? 'Hide' : 'Display' }}
            </button>
            <button
              class="btn-secondary inline-flex h-8 items-center gap-1.5 px-2.5 text-xs"
              type="button"
              :aria-label="`Edit ${group.name}`"
              @click="editGroup(group.id)"
            >
              <Pencil class="h-3.5 w-3.5" />
              Edit
            </button>
          </div>
        </div>

        <template v-else>
          <div
            class="grid grid-cols-[minmax(0,1fr)_auto] gap-x-2 gap-y-2"
            :data-testid="`mana-type-group-editor-${group.id}`"
          >
            <label
              class="field-label col-span-full"
              :for="`mana-group-name-${group.id}`"
            >
              Group name
            </label>
            <input
              :id="`mana-group-name-${group.id}`"
              v-model="group.name"
              class="input-base min-w-0"
              type="text"
              :aria-describedby="groupError(group.id) ? `mana-group-error-${group.id}` : undefined"
            >
            <div class="flex shrink-0 items-center gap-1">
              <button
                class="theme-icon-button"
                type="button"
                :disabled="index === 0"
                :aria-label="`Move ${group.name || 'group'} up`"
                @click="moveGroup(index, -1)"
              >
                <ArrowUp class="h-4 w-4" />
              </button>
              <button
                class="theme-icon-button"
                type="button"
                :disabled="index === draftGroups.length - 1"
                :aria-label="`Move ${group.name || 'group'} down`"
                @click="moveGroup(index, 1)"
              >
                <ArrowDown class="h-4 w-4" />
              </button>
              <button
                class="theme-icon-button theme-error-text"
                type="button"
                :aria-label="`Delete ${group.name || 'group'}`"
                @click="removeGroup(group.id)"
              >
                <Trash2 class="h-4 w-4" />
              </button>
            </div>
          </div>

          <fieldset>
            <legend class="theme-kicker mb-2 text-[11px] font-semibold uppercase tracking-[0.14em]">
              Type rules
            </legend>
            <p class="theme-section-muted mb-2 text-xs">
              Click to cycle: include, exclude, then clear. Keep at least two types active.
            </p>
            <div class="mb-3 flex flex-wrap gap-2">
              <button
                class="btn-secondary h-7 px-2 text-[11px]"
                type="button"
                :aria-label="`Enable all types for ${group.name || 'group'}`"
                @click="setAllTypeRules(group, 'include')"
              >
                Enable all
              </button>
              <button
                class="btn-secondary h-7 px-2 text-[11px]"
                type="button"
                :aria-label="`Disable all types for ${group.name || 'group'}`"
                @click="setAllTypeRules(group, 'exclude')"
              >
                Disable all
              </button>
              <button
                class="btn-secondary h-7 px-2 text-[11px]"
                type="button"
                :aria-label="`Clear all type rules for ${group.name || 'group'}`"
                @click="setAllTypeRules(group, 'off')"
              >
                Clear all
              </button>
            </div>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="type in availableTypes"
                :key="type.key"
                class="theme-choice-chip min-h-9 px-3 text-xs font-medium"
                :class="typeRuleClass(group, type.key)"
                type="button"
                :aria-pressed="typeRule(group, type.key) !== 'off'"
                :aria-label="typeRuleLabel(group, type.key, type.label)"
                @click="toggleTypeRule(group, type.key)"
              >
                <span
                  v-if="typeRule(group, type.key) !== 'off'"
                  aria-hidden="true"
                >
                  {{ typeRule(group, type.key) === 'include' ? '+' : '−' }}
                </span>
                {{ type.label }}
              </button>
            </div>
          </fieldset>

          <p
            v-if="groupError(group.id)"
            :id="`mana-group-error-${group.id}`"
            class="theme-error-text text-xs font-medium"
          >
            {{ groupError(group.id) }}
          </p>
        </template>
      </section>
    </div>

    <div class="theme-divider mt-5 flex flex-wrap items-center justify-between gap-3 border-t pt-4">
      <button
        class="btn-secondary inline-flex items-center gap-2"
        type="button"
        @click="addGroup"
      >
        <Plus class="h-4 w-4" />
        Add group
      </button>
      <div class="flex items-center gap-2">
        <button
          class="btn-secondary"
          type="button"
          @click="requestClose"
        >
          Cancel
        </button>
        <button
          class="btn-primary"
          type="button"
          :disabled="validationErrors.length > 0"
          @click="save"
        >
          Save groups
        </button>
      </div>
    </div>
  </AppModal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ArrowDown, ArrowUp, Eye, EyeOff, Pencil, Plus, Trash2, X } from 'lucide-vue-next';
import AppModal from '@/shared/components/modals/AppModal.vue';
import { isManaTypeKey } from '@/domain/cards/utils/gallery/cardSort';
import {
  getTriStateSelection,
  getTriStateSelectionClass,
  getTriStateSelectionLabel,
  setAllTriStateSelections,
  toggleTriStateSelection,
  type TriStateSelection,
} from '@/domain/cards/utils/filters/triStateSelection';
import type { ManaTypeGroup } from '@/domain/decks/utils/manaDistribution';
import {
  createManaTypeGroupId,
  validateManaTypeGroups,
} from '@/domain/decks/composables/useManaTypeGroups';
import type { DeckMetadataOption } from '@/domain/decks/types';

const props = defineProps<{
  open: boolean;
  groups: ManaTypeGroup[];
  types: DeckMetadataOption[];
}>();

const emit = defineEmits<{
  close: [];
  save: [groups: ManaTypeGroup[]];
}>();

const draftGroups = ref<ManaTypeGroup[]>([]);
const editingGroupIds = ref<Set<string>>(new Set());

const availableTypes = computed(() => props.types.filter((type) => !isManaTypeKey(type.key)));
const availableTypeKeys = computed(
  () => new Set(availableTypes.value.map((type) => type.key.trim().toLowerCase())),
);
const validationErrors = computed(() =>
  validateManaTypeGroups(draftGroups.value, availableTypeKeys.value),
);

const cloneGroups = (groups: ManaTypeGroup[]): ManaTypeGroup[] =>
  groups.map((group) => ({
    ...group,
    typeKeys: [...group.typeKeys],
    excludedTypeKeys: [...group.excludedTypeKeys],
  }));

const groupError = (groupId: string): string =>
  validationErrors.value.find((error) => error.groupId === groupId)?.message ?? '';

const isEditingGroup = (groupId: string): boolean => editingGroupIds.value.has(groupId);

const editGroup = (groupId: string): void => {
  editingGroupIds.value = new Set([...editingGroupIds.value, groupId]);
};

const typeLabel = (typeKey: string): string =>
  availableTypes.value.find((type) => type.key === typeKey)?.label ?? typeKey;

const toggleGroupVisibility = (group: ManaTypeGroup): void => {
  group.isVisible = !group.isVisible;
};

const addGroup = (): void => {
  const groupId = createManaTypeGroupId();
  draftGroups.value.push({
    id: groupId,
    name: '',
    typeKeys: [],
    excludedTypeKeys: [],
    isVisible: true,
  });
  editGroup(groupId);
};

const removeGroup = (groupId: string): void => {
  draftGroups.value = draftGroups.value.filter((group) => group.id !== groupId);
  const nextEditingGroupIds = new Set(editingGroupIds.value);
  nextEditingGroupIds.delete(groupId);
  editingGroupIds.value = nextEditingGroupIds;
};

const moveGroup = (index: number, offset: -1 | 1): void => {
  const targetIndex = index + offset;
  if (targetIndex < 0 || targetIndex >= draftGroups.value.length) {
    return;
  }
  const nextGroups = [...draftGroups.value];
  const [group] = nextGroups.splice(index, 1);
  if (!group) {
    return;
  }
  nextGroups.splice(targetIndex, 0, group);
  draftGroups.value = nextGroups;
};

const typeRule = (group: ManaTypeGroup, typeKey: string): TriStateSelection =>
  getTriStateSelection(typeKey, group.typeKeys, group.excludedTypeKeys);

const typeRuleClass = (group: ManaTypeGroup, typeKey: string): string =>
  getTriStateSelectionClass(typeRule(group, typeKey));

const typeRuleLabel = (group: ManaTypeGroup, typeKey: string, label: string): string =>
  getTriStateSelectionLabel(label, typeRule(group, typeKey));

const toggleTypeRule = (group: ManaTypeGroup, typeKey: string): void => {
  const next = toggleTriStateSelection(typeKey, group.typeKeys, group.excludedTypeKeys);
  group.typeKeys = next.included;
  group.excludedTypeKeys = next.excluded;
};

const setAllTypeRules = (group: ManaTypeGroup, rule: TriStateSelection): void => {
  const typeKeys = availableTypes.value.map((type) => type.key);
  const next = setAllTriStateSelections(typeKeys, rule);
  group.typeKeys = next.included;
  group.excludedTypeKeys = next.excluded;
};

const requestClose = (): void => {
  emit('close');
};

const save = (): void => {
  if (validationErrors.value.length > 0) {
    return;
  }
  emit(
    'save',
    draftGroups.value.map((group) => ({
      id: group.id,
      name: group.name.trim(),
      typeKeys: group.typeKeys.filter((key) =>
        availableTypeKeys.value.has(key.trim().toLowerCase()),
      ),
      excludedTypeKeys: group.excludedTypeKeys.filter((key) =>
        availableTypeKeys.value.has(key.trim().toLowerCase()),
      ),
      isVisible: group.isVisible,
    })),
  );
};

watch(
  () => props.open,
  (open) => {
    if (!open) {
      draftGroups.value = [];
      editingGroupIds.value = new Set();
      return;
    }
    draftGroups.value = cloneGroups(props.groups);
    editingGroupIds.value = new Set();
  },
  { immediate: true },
);
</script>
