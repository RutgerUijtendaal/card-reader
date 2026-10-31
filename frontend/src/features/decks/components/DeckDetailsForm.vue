<template>
  <div class="mx-auto w-full max-w-4xl space-y-9 pb-8">
    <CardBuilderDetailsFields
      v-model:name="deckName"
      v-model:summary="deckDescription"
      v-model:long-description="deckLongDescription"
      kind="Deck"
      field-prefix="deck"
      pool="player"
      description="Give your deck a clear identity and describe how it plays."
      :focus-request="controller.focusDeckNameRequest.value"
    />

    <section class="space-y-5">
      <div class="space-y-1">
        <h2 class="theme-section-title text-lg font-semibold">
          Organization
        </h2>
        <p class="theme-section-muted text-sm">
          Classify your deck and control how it appears to other players.
        </p>
      </div>
      <DeckTagPicker
        sectioned
        :catalog="controller.deckTagCatalog.value"
        :model-value="controller.deck.form.tag_ids"
        :suggested-type-labels="controller.deck.form.suggested_type_labels"
        description="Make this deck easier to find and understand."
        @update:model-value="controller.deck.setDeckTagIds"
        @update:suggested-type-labels="controller.deck.setSuggestedTypeLabels"
      />
      <AppFormSection
        title="Difficulty"
        description="Give players a broad sense of how demanding this deck is to play."
      >
        <div class="flex flex-wrap items-center gap-2">
          <ChoicePill
            v-for="option in difficultyOptions"
            :key="option.value"
            :selected="difficulty === option.value"
            @click="controller.deck.setDeckDifficulty(option.value)"
          >
            {{ option.label }}
          </ChoicePill>
          <button
            v-if="difficulty"
            class="theme-section-muted px-2 py-1 text-sm font-medium transition hover:text-[var(--color-text)]"
            type="button"
            @click="controller.deck.setDeckDifficulty(null)"
          >
            Clear
          </button>
        </div>
      </AppFormSection>
      <AppFormSection
        title="Visibility"
        :description="selectedVisibilityDescription"
      >
        <div class="flex flex-wrap gap-2">
          <ChoicePill
            v-for="option in visibilityOptions"
            :key="option.value"
            :selected="visibility === option.value"
            @click="controller.deck.setDeckVisibility(option.value)"
          >
            {{ option.label }}
          </ChoicePill>
        </div>
      </AppFormSection>
    </section>

    <div class="theme-divider flex justify-end border-t pt-6">
      <button
        class="btn-primary"
        type="button"
        @click="controller.openCards()"
      >
        <span>Continue to Cards</span>
        <ArrowRight
          class="h-4 w-4"
          aria-hidden="true"
        />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { ArrowRight } from 'lucide-vue-next';
import CardBuilderDetailsFields from '@/domain/cards/components/CardBuilderDetailsFields.vue';
import ChoicePill from '@/shared/components/ChoicePill.vue';
import DeckTagPicker from '@/domain/decks/components/DeckTagPicker.vue';
import AppFormSection from '@/shared/components/app/AppFormSection.vue';
import { deckDifficultyOptions } from '@/domain/decks/utils/difficulty';
import { deckVisibilityDescriptions, deckVisibilityOptions } from '@/domain/decks/utils/visibility';
import type { DeckEditorController } from '@/features/decks/composables/useDeckEditor';

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
const difficultyOptions = deckDifficultyOptions;
const difficulty = computed(() => props.controller.deck.form.difficulty);
const visibilityOptions = deckVisibilityOptions;
const visibility = computed(() => props.controller.deck.form.visibility);
const selectedVisibilityDescription = computed(
  () => deckVisibilityDescriptions[visibility.value] ?? '',
);
</script>
