<template>
  <section class="flex h-[calc(100vh-3rem)] min-h-0 flex-col gap-6 overflow-hidden">
    <div class="page-card flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <h2 class="theme-section-title text-xl font-semibold">
          {{ controller.deckId.value ? 'Edit Deck' : 'Build Deck' }}
        </h2>
        <p class="theme-section-muted text-sm">
          {{ controller.deck.isSetupStep.value ? 'Select a hero and enter the deck details to continue.' : `Build a mainboard with at least ${MIN_MAINBOARD_CARD_COUNT} cards, including ${MIN_MAINBOARD_MANA_TYPE_COUNT} Mana cards.` }}
        </p>
      </div>

      <div class="flex flex-col gap-4 lg:min-w-0 lg:flex-row lg:items-center">
        <div
          v-if="!controller.deck.isSetupStep.value"
          class="min-w-0 flex-1"
        >
          <div class="flex flex-wrap items-center gap-x-5 gap-y-2">
            <div class="flex items-baseline gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Total</span>
              <span class="theme-section-title text-base font-semibold">{{ controller.deck.overallTotalCards.value }}</span>
            </div>
            <div class="theme-divider hidden h-4 border-l lg:block" />
            <div class="flex items-baseline gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Main</span>
              <span class="theme-section-title text-base font-semibold">
                {{ controller.deck.totalMainboardCards.value }}<template v-if="controller.deck.totalMainboardCards.value >= MAX_MAINBOARD_CARD_COUNT"> / {{ MAX_MAINBOARD_CARD_COUNT }}</template>
              </span>
            </div>
            <div class="theme-divider hidden h-4 border-l lg:block" />
            <div class="flex items-baseline gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Mana</span>
              <span class="theme-section-title text-base font-semibold">{{ controller.deck.totalMainboardManaTypeCards.value }}</span>
            </div>
            <div class="theme-divider hidden h-4 border-l lg:block" />

            <div
              v-if="controller.deck.headerDeckTypeCounts.value.length > 0"
              class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-sm"
            >
              <span class="theme-kicker shrink-0 text-[11px] font-semibold uppercase tracking-wide">Type Mix</span>
              <span
                v-for="row in controller.deck.headerDeckTypeCounts.value"
                :key="row.type.id"
                class="theme-section-muted"
              >
                <span class="theme-section-title font-medium">{{ row.type.label }}</span>
                {{ row.count }}
              </span>
              <span
                v-if="controller.deck.remainingDeckTypeCount.value > 0"
                class="theme-section-muted"
              >
                +{{ controller.deck.remainingDeckTypeCount.value }} more
              </span>
            </div>
            <p
              v-else
              class="theme-section-muted flex items-center gap-2 text-xs"
            >
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Type Mix</span>
              <span>No type data yet.</span>
            </p>

            <div class="theme-divider hidden h-4 border-l lg:block" />
            <div class="flex items-baseline gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Unique</span>
              <span class="theme-section-title text-base font-semibold">{{ controller.deck.overallUniqueCards.value }}</span>
            </div>
            <div class="theme-divider hidden h-4 border-l lg:block" />
            <div class="flex items-baseline gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Status</span>
              <span
                class="text-base font-semibold"
                :class="controller.deck.isDeckValid.value ? 'text-emerald-300' : 'theme-section-title'"
              >
                {{ controller.deck.deckStatusLabel.value }}
              </span>
            </div>
          </div>
        </div>

        <div
          class="theme-divider flex flex-wrap items-center gap-2 pt-1 lg:shrink-0 lg:border-l lg:pl-4 lg:pt-0"
          :class="!controller.deck.isSetupStep.value ? 'border-t pt-4 lg:border-t-0 lg:pt-0' : ''"
        >
          <RouterLink
            class="btn-secondary"
            to="/my/decks"
          >
            Back to My Decks
          </RouterLink>
          <button
            v-if="!controller.deck.isSetupStep.value"
            class="btn-primary"
            type="button"
            :disabled="controller.saving.value"
            @click="controller.saveDeck"
          >
            {{ controller.saving.value ? 'Saving...' : controller.deckId.value ? 'Save Deck' : 'Create Deck' }}
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="controller.loading.value"
      class="page-card theme-section-muted flex-1 text-sm"
    >
      Loading deck...
    </div>

    <section
      v-else
      class="grid min-h-0 flex-1 gap-6 overflow-hidden xl:grid-cols-[23rem_minmax(0,1fr)_24rem]"
    >
      <DeckBuilderFiltersPanel :controller="controller" />
      <DeckBuilderGallery :controller="controller" />
      <DeckBuilderSummaryPanel :controller="controller" />
    </section>
  </section>
</template>

<script setup lang="ts">
import DeckBuilderFiltersPanel from '@/modules/decks/components/DeckBuilderFiltersPanel.vue';
import DeckBuilderGallery from '@/modules/decks/components/DeckBuilderGallery.vue';
import DeckBuilderSummaryPanel from '@/modules/decks/components/DeckBuilderSummaryPanel.vue';
import { useDeckEditor } from '@/modules/decks/composables/useDeckEditor';
import { MAX_MAINBOARD_CARD_COUNT, MIN_MAINBOARD_CARD_COUNT, MIN_MAINBOARD_MANA_TYPE_COUNT } from '@/modules/decks/constants';

const controller = useDeckEditor();
</script>
