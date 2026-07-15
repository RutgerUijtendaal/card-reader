<template>
  <div
    v-if="open"
    class="theme-overlay fixed inset-0 z-50 flex items-center justify-center p-4"
    role="dialog"
    aria-modal="true"
    aria-labelledby="mana-type-groups-title"
    @click.self="requestClose"
  >
    <div
      ref="dialogRef"
      class="theme-popover app-scrollbar max-h-[90vh] w-full max-w-3xl overflow-y-auto p-5 shadow-xl"
      tabindex="-1"
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
            Combine card types into reusable groups for deck mana statistics.
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
          :data-testid="`mana-type-group-editor-${group.id}`"
        >
          <div class="flex items-start gap-2">
            <label class="field-label min-w-0 flex-1">
              Group name
              <input
                v-model="group.name"
                class="input-base"
                type="text"
                :aria-describedby="groupError(group.id) ? `mana-group-error-${group.id}` : undefined"
              >
            </label>
            <div class="mt-6 flex shrink-0 items-center gap-1">
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
              Included types
            </legend>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="type in availableTypes"
                :key="type.key"
                class="theme-choice-chip min-h-9 px-3 text-xs font-medium"
                :class="group.typeKeys.includes(type.key) ? 'theme-choice-chip-include' : ''"
                type="button"
                :aria-pressed="group.typeKeys.includes(type.key)"
                @click="toggleType(group, type.key)"
              >
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { onKeyStroke, useFocus, useScrollLock } from '@vueuse/core';
import { ArrowDown, ArrowUp, Plus, Trash2, X } from 'lucide-vue-next';
import { isManaTypeKey } from '@/composables/card-gallery/cardSort';
import type { ManaTypeGroup } from '@/composables/decks/manaDistribution';
import {
  createManaTypeGroupId,
  validateManaTypeGroups,
} from '@/composables/decks/useManaTypeGroups';
import type { DeckMetadataOption } from '@/modules/decks/types';

const props = defineProps<{
  open: boolean;
  groups: ManaTypeGroup[];
  types: DeckMetadataOption[];
}>();

const emit = defineEmits<{
  close: [];
  save: [groups: ManaTypeGroup[]];
}>();

const dialogRef = ref<HTMLElement | null>(null);
const draftGroups = ref<ManaTypeGroup[]>([]);
const bodyScrollLocked = useScrollLock(typeof document === 'undefined' ? null : document.body);
const { focused } = useFocus(dialogRef);

const availableTypes = computed(() => props.types.filter((type) => !isManaTypeKey(type.key)));
const availableTypeKeys = computed(
  () => new Set(availableTypes.value.map((type) => type.key.trim().toLowerCase())),
);
const validationErrors = computed(() => validateManaTypeGroups(draftGroups.value, availableTypeKeys.value));

const cloneGroups = (groups: ManaTypeGroup[]): ManaTypeGroup[] =>
  groups.map((group) => ({ ...group, typeKeys: [...group.typeKeys] }));

const groupError = (groupId: string): string =>
  validationErrors.value.find((error) => error.groupId === groupId)?.message ?? '';

const addGroup = (): void => {
  draftGroups.value.push({ id: createManaTypeGroupId(), name: '', typeKeys: [] });
};

const removeGroup = (groupId: string): void => {
  draftGroups.value = draftGroups.value.filter((group) => group.id !== groupId);
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

const toggleType = (group: ManaTypeGroup, typeKey: string): void => {
  group.typeKeys = group.typeKeys.includes(typeKey)
    ? group.typeKeys.filter((key) => key !== typeKey)
    : [...group.typeKeys, typeKey];
};

const requestClose = (): void => {
  emit('close');
};

const save = (): void => {
  if (validationErrors.value.length > 0) {
    return;
  }
  emit('save', draftGroups.value.map((group) => ({
    id: group.id,
    name: group.name.trim(),
    typeKeys: group.typeKeys.filter((key) => availableTypeKeys.value.has(key.trim().toLowerCase())),
  })));
};

onKeyStroke('Escape', (event) => {
  if (!props.open) {
    return;
  }
  event.preventDefault();
  requestClose();
});

watch(
  () => props.open,
  async (open) => {
    bodyScrollLocked.value = open;
    if (!open) {
      draftGroups.value = [];
      return;
    }
    draftGroups.value = cloneGroups(props.groups);
    await nextTick();
    focused.value = true;
  },
  { immediate: true },
);
</script>
