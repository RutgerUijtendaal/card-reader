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
          ref="deckNameInputRef"
          v-model="deckName"
          class="input-base"
          placeholder="Deck name"
          required
        >
      </label>

      <div class="field-label">
        <span>Summary</span>
        <CardMarkupEditor
          v-model="deckDescription"
          label="Deck summary"
          preferred-card-pool="player"
          textarea-id="deck-summary-field"
          min-height-class="min-h-20"
          placeholder="A short summary shown in deck lists"
        />
      </div>

      <div class="field-label">
        <span>Long description</span>
        <CardMarkupEditor
          v-model="deckLongDescription"
          label="Deck long description"
          preferred-card-pool="player"
          textarea-id="deck-long-description-field"
          min-height-class="min-h-64"
          placeholder="Optional notes, strategy, matchups, or other deck information"
        />
      </div>
    </section>

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
          <button
            v-for="option in difficultyOptions"
            :key="option.value"
            class="theme-pill text-sm"
            :class="difficulty === option.value ? 'theme-pill-accent' : 'theme-pill-neutral'"
            type="button"
            :aria-pressed="difficulty === option.value"
            @click="controller.deck.setDeckDifficulty(option.value)"
          >
            {{ option.label }}
          </button>
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
import { computed, nextTick, ref, watch } from 'vue';
import { ArrowRight } from 'lucide-vue-next';
import CardMarkupEditor from '@/domain/cards/components/CardMarkupEditor.vue';
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
const deckNameInputRef = ref<HTMLInputElement | null>(null);
watch(
  () => props.controller.focusDeckNameRequest.value,
  async () => {
    await nextTick();
    deckNameInputRef.value?.focus({ preventScroll: true });
  },
);
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
