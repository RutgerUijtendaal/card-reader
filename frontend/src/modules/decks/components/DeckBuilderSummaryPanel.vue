<template>
  <aside class="page-card flex h-full min-h-0 flex-col">
    <div class="app-scrollbar flex-1 space-y-4 overflow-y-auto pr-1">
      <template v-if="controller.deck.isSetupStep.value">
        <div class="space-y-1">
          <h3 class="theme-section-title text-lg font-semibold">
            Deck Setup
          </h3>
          <p class="theme-section-muted text-sm">
            Enter the deck details and choose a hero.
          </p>
        </div>

        <label class="field-label">
          Name
          <input
            v-model="deckName"
            class="input-base"
            placeholder="Deck name"
          >
        </label>

        <label class="field-label">
          Description
          <textarea
            v-model="deckDescription"
            class="input-base min-h-28"
            placeholder="Optional description"
          />
        </label>

        <label class="theme-section-title flex items-center gap-3 text-sm font-semibold">
          <input
            :checked="isPublic"
            type="checkbox"
            class="theme-checkbox h-4 w-4"
            @change="updateDeckPublic(($event.target as HTMLInputElement).checked)"
          >
          <span>Public deck</span>
        </label>

        <div class="theme-muted-panel space-y-3 p-3">
          <p class="theme-section-title text-sm font-semibold">
            Selected Hero
          </p>
          <div
            v-if="controller.deck.selectedHero.value"
            class="space-y-3"
          >
            <img
              v-if="controller.deck.selectedHero.value.image_url"
              :src="toAbsoluteApiUrl(controller.deck.selectedHero.value.image_url)"
              :alt="controller.deck.selectedHero.value.name"
              class="theme-card-frame max-h-80 w-full rounded-2xl object-contain"
            >
            <div
              v-else
              class="theme-empty-state flex h-52 items-center justify-center rounded-2xl text-sm"
            >
              No hero image
            </div>

            <div class="space-y-1">
              <p class="theme-section-title text-sm font-semibold">
                {{ controller.deck.selectedHero.value.name }}
              </p>
              <p class="theme-section-muted text-xs">
                {{ controller.deck.selectedHero.value.label }}
              </p>
            </div>
          </div>
          <p
            v-else
            class="theme-section-muted text-sm"
          >
            No hero selected.
          </p>
        </div>

        <div
          v-if="controller.deck.setupMessages.value.length > 0"
          class="theme-muted-panel space-y-2 p-3"
        >
          <p class="theme-section-title text-sm font-semibold">
            Missing Setup
          </p>
          <p
            v-for="message in controller.deck.setupMessages.value"
            :key="message"
            class="theme-error-text text-sm"
          >
            {{ message }}
          </p>
        </div>

        <button
          class="btn-primary w-full justify-center"
          type="button"
          :disabled="controller.deck.setupMessages.value.length > 0"
          @click="controller.lockSetup"
        >
          Continue
        </button>
      </template>

      <template v-else>
        <div class="theme-muted-panel space-y-3 p-3">
          <div class="flex items-start justify-between gap-3">
            <h3 class="theme-section-title truncate text-lg font-semibold">
              {{ controller.deck.form.name || 'Untitled Deck' }}
            </h3>
            <button
              class="btn-secondary px-2 py-1 text-xs"
              type="button"
              @click="controller.setBuilderStep('setup')"
            >
              Change
            </button>
          </div>

          <div
            v-if="controller.deck.selectedHero.value"
            class="space-y-3"
          >
            <img
              v-if="controller.deck.selectedHero.value.image_url"
              :src="toAbsoluteApiUrl(controller.deck.selectedHero.value.image_url)"
              :alt="controller.deck.selectedHero.value.name"
              class="theme-card-frame max-h-[32rem] w-full rounded-2xl object-contain"
            >
            <div
              v-else
              class="theme-empty-state flex h-52 items-center justify-center rounded-2xl text-sm"
            >
              No hero image
            </div>
          </div>
        </div>

        <div
          v-if="controller.deck.validationMessages.value.length > 0"
          class="theme-muted-panel space-y-2 p-3"
        >
          <p class="theme-section-title text-sm font-semibold">
            Validation
          </p>
          <p
            v-for="message in controller.deck.validationMessages.value"
            :key="message"
            class="theme-error-text text-sm"
          >
            {{ message }}
          </p>
        </div>

        <DeckManaCurve
          :entries="controller.deck.detailedEntries.value"
          empty-label="Add mainboard cards to see the mana curve."
        />

        <div class="space-y-3">
          <h4 class="theme-section-title text-sm font-semibold">
            Deck List
          </h4>

          <div
            v-if="controller.deck.detailedEntries.value.length === 0"
            class="theme-empty-state"
          >
            No cards added yet.
          </div>

          <div
            v-for="entry in controller.deck.detailedEntries.value"
            :key="entry.card.id"
            class="theme-card-frame flex items-center gap-3 rounded-2xl px-3 py-2"
          >
            <div class="min-w-0 flex-1">
              <p class="theme-section-title truncate text-sm font-semibold">
                {{ entry.card.name }}
              </p>
            </div>

            <div class="flex items-center gap-2">
              <button
                class="btn-secondary h-8 w-8 px-0"
                type="button"
                @click="controller.deck.changeQuantity(entry.card.id, -1)"
              >
                -
              </button>
              <input
                :value="entry.quantity"
                class="input-base h-8 w-12 px-1 text-center text-sm"
                type="number"
                min="1"
                max="4"
                @input="controller.deck.setQuantity(entry.card.id, ($event.target as HTMLInputElement).value)"
              >
              <button
                class="btn-secondary h-8 w-8 px-0"
                type="button"
                :disabled="entry.quantity >= 4"
                @click="controller.deck.changeQuantity(entry.card.id, 1)"
              >
                +
              </button>
            </div>

            <button
              class="theme-section-muted shrink-0 px-1 text-base font-semibold transition hover:text-rose-300"
              type="button"
              aria-label="Remove card from deck"
              @click="controller.deck.removeEntry(entry.card.id)"
            >
              X
            </button>
          </div>
        </div>
      </template>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';
import DeckManaCurve from '@/modules/decks/components/DeckManaCurve.vue';
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

const isPublic = computed(() => props.controller.deck.form.is_public);

const updateDeckPublic = (value: boolean): void => {
  props.controller.deck.setDeckPublic(value);
};
</script>
