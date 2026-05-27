<template>
  <section class="space-y-5">
    <AppPageHeader
      :icon="Folders"
      title="My Decks"
      subtitle="Manage your private, unlisted, and public decks."
      :back-to="backLink"
      :back-label="backLabel"
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <RouterLink
          class="btn-primary"
          :to="newDeckLocation"
        >
          New Deck
        </RouterLink>
      </template>
    </AppPageHeader>

    <div
      v-if="loading"
      class="page-card theme-section-muted text-sm"
    >
      Loading your decks...
    </div>

    <div
      v-else-if="decks.length === 0"
      class="page-card theme-section-muted text-sm"
    >
      You do not have any decks yet.
    </div>

    <div
      v-else
      class="grid gap-4 xl:grid-cols-2"
    >
      <DeckListCard
        v-for="deck in decks"
        :key="deck.id"
        :deck="deck"
        mode="owned"
        :title-to="`/my/decks/${deck.id}`"
      >
        <template #actions>
          <div class="flex h-full min-h-[7.5rem] min-w-[11rem] max-w-[11rem] flex-col justify-between">
            <div class="flex items-center gap-2">
              <RouterLink
                class="btn-secondary flex-1"
                :to="buildMyDeckEditorLocation(deck.id)"
              >
                Edit
              </RouterLink>
              <ExtraActionsMenu button-label="Open deck actions">
                <template #default="{ close }">
                  <button
                    v-if="canShareDeck(deck)"
                    class="btn-secondary w-full justify-center"
                    type="button"
                    @click="copyShareLink(deck); close()"
                  >
                    Copy Share Link
                  </button>

                  <button
                    class="btn-secondary w-full justify-center"
                    type="button"
                    @click="exportDeck(deck); close()"
                  >
                    Export TTS
                  </button>

                  <button
                    class="btn-danger-secondary w-full justify-center"
                    type="button"
                    @click="promptDelete(deck); close()"
                  >
                    Delete
                  </button>
                </template>
              </ExtraActionsMenu>
            </div>

            <label class="flex flex-col gap-1 text-xs">
              <span class="theme-section-muted">Visibility</span>
              <AppSelect
                wrapper-class="min-w-0"
                :disabled="savingDeckIds.has(deck.id)"
                :model-value="deck.visibility"
                :options="visibilityOptions"
                @update:model-value="handleVisibilitySelect(deck, $event)"
              />
            </label>
          </div>
        </template>
      </DeckListCard>
    </div>

    <ConfirmModal
      :open="deleteTarget !== null"
      title="Delete Deck"
      :message="deleteTarget ? `Delete deck '${deleteTarget.name}'?` : ''"
      confirm-label="Delete"
      cancel-label="Cancel"
      :loading="deleting"
      loading-label="Deleting..."
      @cancel="deleteTarget = null"
      @confirm="confirmDelete"
    />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { computed } from 'vue';
import { Folders } from 'lucide-vue-next';
import { toast } from 'vue-sonner';
import { useRoute } from 'vue-router';
import AppSelect from '@/components/app/AppSelect.vue';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import ExtraActionsMenu from '@/components/app/ExtraActionsMenu.vue';
import ConfirmModal from '@/components/modals/ConfirmModal.vue';
import { deleteDeck, fetchMyDecks, updateDeck } from '@/modules/decks/api';
import DeckListCard from '@/modules/decks/components/DeckListCard.vue';
import { buildDeckUpsertRequestFromRecord } from '@/modules/decks/deckPayload';
import {
  buildMyDeckEditorLocation,
  buildMyDecksReturnLocation,
  buildNewDeckEditorLocation,
  getMyDecksReturnLabel,
} from '@/modules/decks/deckRouteState';
import { buildDeckShareUrl, canShareDeck } from '@/modules/decks/share';
import type { DeckRecord, DeckVisibility } from '@/modules/decks/types';
import { useDeckExport } from '@/modules/decks/useDeckExport';
import { deckVisibilityLabels, deckVisibilityOptions } from '@/modules/decks/visibility';

const route = useRoute();
const decks = ref<DeckRecord[]>([]);
const loading = ref(false);
const deleting = ref(false);
const deleteTarget = ref<DeckRecord | null>(null);
const savingDeckIds = ref(new Set<string>());
const visibilityOptions = deckVisibilityOptions;
const { exportTtsDeck } = useDeckExport();
const backLink = computed(() => buildMyDecksReturnLocation(route.query));
const backDestinationLabel = computed(() => getMyDecksReturnLabel(route.query));
const backLabel = computed(() => (backDestinationLabel.value ? `Back to ${backDestinationLabel.value}` : ''));
const newDeckLocation = computed(() =>
  buildNewDeckEditorLocation(backDestinationLabel.value === 'Decks' ? 'decks' : 'my_decks'),
);

const loadDecks = async (): Promise<void> => {
  loading.value = true;
  try {
    decks.value = await fetchMyDecks();
  } finally {
    loading.value = false;
  }
};

const promptDelete = (deck: DeckRecord): void => {
  deleteTarget.value = deck;
};

const updateDeckVisibility = async (deck: DeckRecord, visibility: DeckVisibility): Promise<void> => {
  if (deck.visibility === visibility) {
    return;
  }
  savingDeckIds.value = new Set(savingDeckIds.value).add(deck.id);
  try {
    const nextDeck = await updateDeck(deck.id, {
      ...buildDeckUpsertRequestFromRecord(deck),
      visibility,
    });
    decks.value = decks.value.map((entry) => (entry.id === nextDeck.id ? nextDeck : entry));
    toast.success(`Deck is now ${deckVisibilityLabels[nextDeck.visibility].toLowerCase()}.`);
  } catch {
    toast.error('Unable to update deck visibility.');
  } finally {
    const nextSavingDeckIds = new Set(savingDeckIds.value);
    nextSavingDeckIds.delete(deck.id);
    savingDeckIds.value = nextSavingDeckIds;
  }
};

const handleVisibilitySelect = (deck: DeckRecord, value: string | number | null): void => {
  if (value === 'private' || value === 'unlisted' || value === 'public') {
    void updateDeckVisibility(deck, value);
  }
};

const copyShareLink = async (deck: DeckRecord): Promise<void> => {
  if (!canShareDeck(deck)) {
    return;
  }
  await navigator.clipboard.writeText(buildDeckShareUrl(deck.id));
  toast.success('Share link copied.');
};

const exportDeck = async (deck: DeckRecord): Promise<void> => {
  await exportTtsDeck(deck.id, deck.name);
};

const confirmDelete = async (): Promise<void> => {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    await deleteDeck(deleteTarget.value.id);
    decks.value = decks.value.filter((deck) => deck.id !== deleteTarget.value?.id);
    deleteTarget.value = null;
    toast.success('Deck deleted.');
  } finally {
    deleting.value = false;
  }
};

onMounted(loadDecks);
</script>
