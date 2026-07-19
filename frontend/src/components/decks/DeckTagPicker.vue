<template>
  <div class="space-y-2">
    <div class="flex items-center justify-between gap-3">
      <p class="theme-section-title text-sm font-semibold">
        Tags
      </p>
      <button
        ref="triggerRef"
        type="button"
        class="theme-icon-button"
        title="Add deck tags"
        aria-label="Add deck tags"
        :aria-expanded="isOpen"
        @click="toggle"
      >
        <Plus class="h-4 w-4" />
      </button>
    </div>

    <div
      v-if="selectedTags.length > 0 || suggestedTypeLabels.length > 0"
      class="flex flex-wrap gap-2"
    >
      <button
        v-for="tag in selectedTags"
        :key="tag.id"
        type="button"
        class="theme-pill inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold"
        :class="tag.kind === 'role' ? 'theme-pill-accent' : 'theme-pill-keyword'"
        :aria-label="`Remove ${tag.label}`"
        @click="toggleTag(tag.id)"
      >
        {{ tag.label }}
        <X class="h-3 w-3" />
      </button>
      <button
        v-for="label in suggestedTypeLabels"
        :key="label"
        type="button"
        class="theme-pill theme-pill-neutral inline-flex items-center gap-1 border border-dashed px-2 py-1 text-xs font-semibold"
        :aria-label="`Remove pending suggestion ${label}`"
        @click="removeSuggestion(label)"
      >
        {{ label }} · Pending
        <X class="h-3 w-3" />
      </button>
    </div>

    <div
      v-if="selectedTags.length === 0"
      class="flex flex-wrap gap-2"
    >
      <button
        v-for="role in catalog.roles"
        :key="role.id"
        type="button"
        class="theme-choice-chip px-3 py-1.5 text-xs font-semibold"
        @click="toggleTag(role.id)"
      >
        {{ role.label }}
      </button>
    </div>

    <Teleport to="body">
      <div
        v-if="isOpen"
        ref="panelRef"
        class="theme-popover z-50 w-80 p-3 shadow-xl"
        :style="{ position: 'fixed', left: `${x}px`, top: `${y}px` }"
      >
        <div class="space-y-3">
          <input
            v-model="searchTerm"
            class="input-base"
            placeholder="Search or suggest a type..."
            autofocus
          >

          <div
            v-for="group in filteredGroups"
            :key="group.kind"
            class="space-y-1.5"
          >
            <p class="theme-kicker text-[11px] font-semibold uppercase tracking-[0.16em]">
              {{ group.label }}
            </p>
            <button
              v-for="tag in group.tags"
              :key="tag.id"
              type="button"
              class="theme-ghost-button flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm"
              @click="toggleTag(tag.id)"
            >
              <span>{{ tag.label }}</span>
              <Check
                v-if="selectedIds.has(tag.id)"
                class="h-4 w-4 text-[var(--theme-accent)]"
              />
            </button>
          </div>

          <button
            v-if="canSuggestSearch"
            type="button"
            class="theme-divider flex w-full items-center gap-2 border-t px-2 pt-3 text-left text-sm font-semibold text-[var(--theme-accent)]"
            @click="suggestSearch"
          >
            <Plus class="h-4 w-4" />
            Suggest type "{{ normalizedSearchLabel }}"
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Check, Plus, X } from 'lucide-vue-next';
import { useFloatingPopover } from '@/composables/useFloatingPopover';
import type { DeckTagCatalog, DeckTagOption } from '@/modules/decks/types';

const props = defineProps<{
  catalog: DeckTagCatalog;
  modelValue: string[];
  suggestedTypeLabels: string[];
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void;
  (e: 'update:suggestedTypeLabels', value: string[]): void;
}>();

const { isOpen, triggerRef, panelRef, x, y, toggle, close } = useFloatingPopover();
const searchTerm = ref('');
const allTags = computed(() => [...props.catalog.roles, ...props.catalog.types]);
const selectedIds = computed(() => new Set(props.modelValue));
const selectedTags = computed(() => allTags.value.filter((tag) => selectedIds.value.has(tag.id)));
const normalizedSearchLabel = computed(() => searchTerm.value.trim().replace(/\s+/g, ' '));
const normalizedSearch = computed(() => normalizedSearchLabel.value.toLocaleLowerCase());
const matchesSearch = (tag: DeckTagOption): boolean =>
  !normalizedSearch.value ||
  tag.label.toLocaleLowerCase().includes(normalizedSearch.value) ||
  tag.key.toLocaleLowerCase().includes(normalizedSearch.value);
const filteredGroups = computed(() =>
  [
    { kind: 'role', label: 'Roles', tags: props.catalog.roles.filter(matchesSearch) },
    { kind: 'type', label: 'Types', tags: props.catalog.types.filter(matchesSearch) },
  ].filter((group) => group.tags.length > 0),
);
const canSuggestSearch = computed(() => {
  if (!normalizedSearch.value) return false;
  const matchesKnownType = props.catalog.types.some(
    (tag) =>
      tag.label.toLocaleLowerCase() === normalizedSearch.value ||
      tag.key === normalizedSearch.value,
  );
  const matchesPending = props.suggestedTypeLabels.some(
    (label) => label.toLocaleLowerCase() === normalizedSearch.value,
  );
  return !matchesKnownType && !matchesPending;
});

watch(isOpen, (open) => {
  if (!open) searchTerm.value = '';
});

const toggleTag = (tagId: string): void => {
  const next = new Set(props.modelValue);
  if (next.has(tagId)) {
    next.delete(tagId);
  } else {
    next.add(tagId);
  }
  emit('update:modelValue', [...next]);
};

const removeSuggestion = (label: string): void => {
  emit(
    'update:suggestedTypeLabels',
    props.suggestedTypeLabels.filter((item) => item !== label),
  );
};

const suggestSearch = (): void => {
  if (!canSuggestSearch.value) return;
  emit('update:suggestedTypeLabels', [...props.suggestedTypeLabels, normalizedSearchLabel.value]);
  close();
};
</script>
