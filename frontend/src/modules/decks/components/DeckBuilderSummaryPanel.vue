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

        <div class="space-y-2">
          <p class="theme-section-title text-sm font-semibold">
            Visibility
          </p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="option in visibilityOptions"
              :key="option.value"
              class="theme-pill text-xs"
              :class="visibility === option.value ? 'theme-pill-accent' : 'theme-pill-neutral'"
              type="button"
              @click="updateDeckVisibility(option.value)"
            >
              {{ option.label }}
            </button>
          </div>
          <p class="theme-section-muted text-xs">
            {{ selectedVisibilityDescription }}
          </p>
        </div>

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
          :entries="controller.deck.detailedMainboardEntries.value"
          empty-label="Add mainboard cards to see the mana curve."
        />

        <div class="space-y-3">
          <div class="flex items-center justify-between gap-3">
            <h4 class="theme-section-title text-sm font-semibold">
              Deck Boards
            </h4>
            <button
              class="btn-secondary px-2 py-1 text-xs"
              type="button"
              @click="controller.deck.addSideboard()"
            >
              Add Sideboard
            </button>
          </div>

          <div
            v-if="controller.deck.sideboardTabs.value.length > 0"
            class="flex flex-wrap gap-2"
          >
            <button
              class="theme-pill text-xs"
              :class="controller.deck.activeBoardId.value === 'mainboard' ? 'theme-pill-accent' : 'theme-pill-neutral'"
              type="button"
              @click="controller.deck.selectBoard('mainboard')"
            >
              Mainboard ({{ controller.deck.totalMainboardCards.value }})
            </button>
            <button
              v-for="sideboard in controller.deck.sideboardTabs.value"
              :key="sideboard.id"
              class="theme-pill text-xs"
              :class="controller.deck.activeBoardId.value === sideboard.id ? 'theme-pill-accent' : 'theme-pill-neutral'"
              type="button"
              @click="selectSideboard(sideboard.id)"
            >
              {{ sideboard.name }} ({{ sideboard.totalCards }})
            </button>
          </div>

          <div
            v-if="controller.deck.activeSideboard.value"
            class="theme-muted-panel space-y-3 p-3"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="theme-section-title truncate text-sm font-semibold">
                  {{ controller.deck.activeSideboard.value.name || 'Untitled Sideboard' }}
                </p>
                <p class="theme-section-muted text-xs">
                  {{ controller.deck.activeSideboard.value.entries.length }} unique / {{ controller.deck.activeSideboard.value.entries.reduce((sum, entry) => sum + entry.quantity, 0) }} cards
                </p>
              </div>
              <div class="flex shrink-0 items-center gap-2">
                <button
                  class="btn-secondary px-2 py-1 text-xs"
                  type="button"
                  @click="toggleRename()"
                >
                  {{ renamingSideboard ? 'Done' : 'Rename' }}
                </button>
                <button
                  class="btn-secondary px-2 py-1 text-xs"
                  type="button"
                  @click="controller.deck.removeSideboard(controller.deck.activeSideboard.value.id)"
                >
                  Remove
                </button>
              </div>
            </div>
            <label
              v-if="renamingSideboard"
              class="field-label"
            >
              Sideboard Name
              <input
                :value="controller.deck.activeSideboard.value.name"
                class="input-base"
                placeholder="Sideboard name"
                @input="controller.deck.renameSideboard(controller.deck.activeSideboard.value?.id ?? '', ($event.target as HTMLInputElement).value)"
              >
            </label>
            <p
              v-else
              class="theme-section-muted text-xs"
            >
              Active sideboard cards are managed from the gallery and list below.
            </p>
          </div>

          <div
            v-if="controller.deck.detailedActiveBoardEntries.value.length === 0"
            class="theme-empty-state"
          >
            No cards added to this board yet.
          </div>

          <DeckBuilderBoardEntryRow
            v-for="entry in controller.deck.detailedActiveBoardEntries.value"
            :key="entry.card.id"
            :entry="entry"
            :hover-mode="controller.filters.hoverMode.value"
            :quantity-max="controller.deck.activeBoardId.value === 'mainboard' ? 4 : undefined"
            @decrement="controller.deck.changeQuantity($event, -1)"
            @increment="controller.deck.changeQuantity($event, 1)"
            @set-quantity="controller.deck.setQuantity"
            @remove="controller.deck.removeEntry"
          />
        </div>
      </template>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';
import DeckBuilderBoardEntryRow from '@/modules/decks/components/DeckBuilderBoardEntryRow.vue';
import DeckManaCurve from '@/modules/decks/components/DeckManaCurve.vue';
import type { DeckEditorController } from '@/modules/decks/composables/useDeckEditor';
import type { DeckVisibility } from '@/modules/decks/types';
import { deckVisibilityDescriptions, deckVisibilityOptions } from '@/modules/decks/visibility';

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

const visibilityOptions = deckVisibilityOptions;
const visibility = computed(() => props.controller.deck.form.visibility);
const selectedVisibilityDescription = computed(() => deckVisibilityDescriptions[visibility.value] ?? '');
const renamingSideboard = ref(false);

const updateDeckVisibility = (value: DeckVisibility): void => {
  props.controller.deck.setDeckVisibility(value);
};

const selectSideboard = (sideboardId: string): void => {
  props.controller.deck.selectBoard(sideboardId);
  renamingSideboard.value = false;
};

const toggleRename = (): void => {
  renamingSideboard.value = !renamingSideboard.value;
};
</script>
