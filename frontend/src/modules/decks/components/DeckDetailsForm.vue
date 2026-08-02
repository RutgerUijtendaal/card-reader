<template>
  <div class="mx-auto w-full max-w-4xl space-y-9 pb-8">
    <section class="space-y-5">
      <div class="space-y-1">
        <h2 class="theme-section-title text-xl font-semibold">
          Deck details
        </h2>
        <p class="theme-section-muted text-sm">
          Give your deck a clear identity and describe how it plays.
        </p>
      </div>

      <label
        for="deck-name-field"
        class="field-label"
      >
        <span>Name <span class="theme-error-text">*</span></span>
        <input
          id="deck-name-field"
          v-model="deckName"
          class="input-base"
          placeholder="Deck name"
          required
        >
      </label>

      <label
        for="deck-summary-field"
        class="field-label"
      >
        Summary
        <textarea
          id="deck-summary-field"
          v-model="deckDescription"
          class="input-base min-h-20 resize-y"
          placeholder="A short summary shown in deck lists"
        />
      </label>

      <label
        for="deck-long-description-field"
        class="field-label"
      >
        Long description
        <textarea
          id="deck-long-description-field"
          v-model="deckLongDescription"
          class="input-base min-h-64 resize-y"
          placeholder="Optional notes, strategy, matchups, or other deck information"
        />
      </label>
    </section>

    <section class="space-y-5">
      <div class="space-y-1">
        <h2 class="theme-section-title text-lg font-semibold">
          Organization
        </h2>
        <p class="theme-section-muted text-sm">
          Tags make this deck easier to find and understand.
        </p>
      </div>
      <DeckTagPicker
        :catalog="controller.deckTagCatalog.value"
        :model-value="controller.deck.form.tag_ids"
        :suggested-type-labels="controller.deck.form.suggested_type_labels"
        @update:model-value="controller.deck.setDeckTagIds"
        @update:suggested-type-labels="controller.deck.setSuggestedTypeLabels"
      />
    </section>

    <section class="space-y-3">
      <div class="space-y-1">
        <h2 class="theme-section-title text-lg font-semibold">
          Visibility
        </h2>
        <p class="theme-section-muted text-sm">
          Control who can discover and view this deck.
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="option in visibilityOptions"
          :key="option.value"
          class="theme-pill text-sm"
          :class="visibility === option.value ? 'theme-pill-accent' : 'theme-pill-neutral'"
          type="button"
          :aria-pressed="visibility === option.value"
          @click="controller.deck.setDeckVisibility(option.value)"
        >
          {{ option.label }}
        </button>
      </div>
      <p class="theme-section-muted text-sm">
        {{ selectedVisibilityDescription }}
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import DeckTagPicker from '@/components/decks/DeckTagPicker.vue';
import { deckVisibilityDescriptions, deckVisibilityOptions } from '@/composables/decks/visibility';
import type { DeckEditorController } from '@/modules/decks/composables/useDeckEditor';

const props = defineProps<{
  controller: DeckEditorController;
}>();

const deckName = computed({
  get: () => props.controller.deck.form.name,
  set: props.controller.deck.setDeckName,
});
const deckDescription = computed({
  get: () => props.controller.deck.form.description,
  set: props.controller.deck.setDeckDescription,
});
const deckLongDescription = computed({
  get: () => props.controller.deck.form.long_description,
  set: props.controller.deck.setDeckLongDescription,
});
const visibilityOptions = deckVisibilityOptions;
const visibility = computed(() => props.controller.deck.form.visibility);
const selectedVisibilityDescription = computed(
  () => deckVisibilityDescriptions[visibility.value] ?? '',
);
</script>
