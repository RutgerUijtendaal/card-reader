<template>
  <AppStickyAside
    side="right"
  >
    <div class="space-y-5">
      <div class="space-y-1">
        <h3 class="theme-section-title text-lg font-semibold">
          {{ controller.isChangingHero.value ? 'Change Hero' : 'Deck Setup' }}
        </h3>
        <p class="theme-section-muted text-sm">
          {{
            controller.isChangingHero.value
              ? 'Choose a replacement, then apply it to your deck.'
              : 'Choose a hero and name your deck to get started.'
          }}
        </p>
      </div>

      <section class="space-y-3">
        <p class="theme-section-title text-sm font-semibold">
          Selected Hero
        </p>
        <div
          v-if="controller.deck.selectedHero.value"
          class="space-y-3"
        >
          <div
            v-if="controller.deck.selectedHero.value.image_url"
            class="mx-auto aspect-[63/88] max-h-[34rem] w-full rounded-xl"
          >
            <img
              :src="toAbsoluteApiUrl(controller.deck.selectedHero.value.image_url)"
              :alt="controller.deck.selectedHero.value.name"
              class="h-full w-full object-contain"
            >
          </div>
          <div
            v-else
            class="theme-empty-state flex h-[34rem] items-center justify-center rounded-xl text-sm"
          >
            No hero image
          </div>
          <p class="theme-section-title text-center text-sm font-semibold">
            {{ controller.deck.selectedHero.value.name }}
          </p>
        </div>
        <div
          v-else
          class="theme-card-frame mx-auto aspect-[63/88] max-h-[34rem] w-full overflow-hidden rounded-xl"
        >
          <CardLoadingSkeleton :animated="false" />
        </div>
      </section>

      <div
        v-if="!controller.isChangingHero.value && setupBlockingMessages.length > 0"
        class="theme-muted-panel space-y-2 p-3"
      >
        <p class="theme-section-title text-sm font-semibold">
          Setup Issues
        </p>
        <p
          v-for="message in setupBlockingMessages"
          :key="message"
          class="theme-error-text text-sm"
        >
          {{ message }}
        </p>
      </div>

      <label
        v-if="!controller.isChangingHero.value"
        class="field-label"
      >
        <span>Name <span class="theme-error-text">*</span></span>
        <input
          ref="deckNameInputRef"
          v-model="deckName"
          class="input-base"
          placeholder="Deck name"
          required
          @keydown.enter.prevent="continueSetup"
        >
      </label>
    </div>

    <template #footer>
      <div
        v-if="controller.isChangingHero.value"
        class="grid grid-cols-2 gap-2"
      >
        <button
          class="btn-secondary justify-center"
          type="button"
          @click="controller.cancelHeroChange()"
        >
          Cancel
        </button>
        <button
          class="btn-primary justify-center"
          type="button"
          :disabled="!controller.canApplyHeroChange.value"
          @click="controller.applyHeroChange()"
        >
          Apply
        </button>
      </div>
      <button
        v-else
        class="btn-primary w-full justify-center"
        type="button"
        :disabled="!canContinueSetup"
        @click="continueSetup"
      >
        Continue
      </button>
    </template>
  </AppStickyAside>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';
import AppStickyAside from '@/components/app/AppStickyAside.vue';
import CardLoadingSkeleton from '@/components/cards/CardLoadingSkeleton.vue';
import type { DeckEditorController } from '@/modules/decks/composables/useDeckEditor';

const props = defineProps<{
  controller: DeckEditorController;
}>();

const deckName = computed({
  get: () => props.controller.deck.form.name,
  set: props.controller.deck.setDeckName,
});
const setupBlockingMessages = computed(() => [
  ...props.controller.deck.setupMessages.value,
  ...props.controller.deck.blockingMessages.value,
]);
const canContinueSetup = computed(() =>
  Boolean(
    props.controller.deck.selectedHero.value
      && deckName.value.trim()
      && setupBlockingMessages.value.length === 0,
  ),
);
const deckNameInputRef = ref<HTMLInputElement | null>(null);

watch(
  () => props.controller.deck.selectedHero.value?.id ?? '',
  async (heroId, previousHeroId) => {
    if (
      !heroId
      || heroId === previousHeroId
      || props.controller.isChangingHero.value
    ) {
      return;
    }
    await nextTick();
    deckNameInputRef.value?.focus({ preventScroll: true });
  },
);

const continueSetup = (): void => {
  if (canContinueSetup.value) {
    void props.controller.completeInitialHeroSelection();
  }
};
</script>
