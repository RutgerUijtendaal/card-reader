<template>
  <div class="relative">
    <div class="flex items-center gap-2">
      <input
        :value="inputValue"
        class="input-base flex-1"
        :placeholder="selectedCard ? 'Change preview card...' : 'Select preview card...'"
        @focus="open = true"
        @blur="handleBlur"
        @input="handleInput"
      >
      <button
        class="btn-secondary shrink-0 px-3 py-2 text-xs"
        type="button"
        :title="scopeButtonTitle"
        @mousedown.prevent
        @click="toggleScope"
      >
        {{ scopeButtonLabel }}
      </button>
    </div>

    <div
      v-if="open"
      class="theme-popover absolute left-0 right-0 top-full z-20 mt-2 overflow-hidden rounded-xl shadow-xl"
    >
      <div
        v-if="loading"
        class="theme-section-muted px-3 py-3 text-sm"
      >
        Loading preview cards...
      </div>
      <div
        v-else-if="cards.length === 0"
        class="theme-section-muted px-3 py-3 text-sm"
      >
        No matching cards found.
      </div>
      <div
        v-else
        class="app-scrollbar max-h-64 overflow-y-auto p-2"
      >
        <button
          v-for="card in cards"
          :key="card.id"
          class="w-full rounded-lg border px-3 py-2 text-left transition"
          :class="selectedCard?.id === card.id ? 'theme-selected-surface' : 'theme-card-frame hover:-translate-y-0.5'"
          type="button"
          @mousedown.prevent="selectCard(card)"
        >
          <div class="truncate text-sm font-medium">
            {{ card.name }}
          </div>
          <div class="theme-section-muted truncate text-xs">
            {{ card.label }} · {{ card.template_id }}
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { TemplatePreviewCardOption, TemplatePreviewScope } from '@/modules/settings/types';

const props = defineProps<{
  cards: TemplatePreviewCardOption[];
  loading: boolean;
  scope: TemplatePreviewScope;
  searchQuery: string;
  selectedCard: TemplatePreviewCardOption | null;
  templateScopeAvailable: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:scope', value: TemplatePreviewScope): void;
  (e: 'update:searchQuery', value: string): void;
  (e: 'select', value: TemplatePreviewCardOption): void;
}>();

const open = ref(false);

const inputValue = computed(() => props.searchQuery || props.selectedCard?.name || '');
const scopeButtonLabel = computed(() => (props.scope === 'current-template' ? 'This Template' : 'All Cards'));
const scopeButtonTitle = computed(() =>
  props.scope === 'current-template'
    ? 'Searching preview cards from this template'
    : 'Searching preview cards from all templates',
);

const handleInput = (event: Event): void => {
  open.value = true;
  emit('update:searchQuery', (event.target as HTMLInputElement).value);
};

const handleBlur = (): void => {
  window.setTimeout(() => {
    open.value = false;
    emit('update:searchQuery', '');
  }, 120);
};

const selectCard = (card: TemplatePreviewCardOption): void => {
  emit('select', card);
  emit('update:searchQuery', '');
  open.value = false;
};

const toggleScope = (): void => {
  if (!props.templateScopeAvailable) {
    emit('update:scope', 'all-cards');
    return;
  }
  emit('update:scope', props.scope === 'current-template' ? 'all-cards' : 'current-template');
};
</script>
