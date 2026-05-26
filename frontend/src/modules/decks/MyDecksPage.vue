<template>
  <section class="space-y-5">
    <div class="page-card flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 class="theme-section-title text-xl font-semibold">
          My Decks
        </h2>
        <p class="theme-section-muted text-sm">
          Manage your private and public decks.
        </p>
      </div>

      <RouterLink
        class="btn-primary"
        :to="buildNewDeckEditorLocation()"
      >
        New Deck
      </RouterLink>
    </div>

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
      >
        <template #actions>
          <RouterLink
            class="btn-secondary"
            :to="`/my/decks/${deck.id}`"
          >
            Open
          </RouterLink>
          <RouterLink
            class="btn-secondary"
            :to="buildMyDeckEditorLocation(deck.id)"
          >
            Edit
          </RouterLink>
          <button
            class="btn-secondary"
            type="button"
            :disabled="savingDeckIds.has(deck.id)"
            @click="toggleDeckVisibility(deck)"
          >
            {{ savingDeckIds.has(deck.id) ? 'Saving...' : deck.is_public ? 'Make Private' : 'Make Public' }}
          </button>
          <button
            class="btn-danger-secondary"
            type="button"
            @click="promptDelete(deck)"
          >
            Delete
          </button>
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
import { toast } from 'vue-sonner';
import ConfirmModal from '@/components/modals/ConfirmModal.vue';
import { deleteDeck, fetchMyDecks, updateDeck } from '@/modules/decks/api';
import DeckListCard from '@/modules/decks/components/DeckListCard.vue';
import { buildDeckUpsertRequestFromRecord } from '@/modules/decks/deckPayload';
import { buildMyDeckEditorLocation, buildNewDeckEditorLocation } from '@/modules/decks/deckRouteState';
import type { DeckRecord } from '@/modules/decks/types';

const decks = ref<DeckRecord[]>([]);
const loading = ref(false);
const deleting = ref(false);
const deleteTarget = ref<DeckRecord | null>(null);
const savingDeckIds = ref(new Set<string>());

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

const toggleDeckVisibility = async (deck: DeckRecord): Promise<void> => {
  savingDeckIds.value = new Set(savingDeckIds.value).add(deck.id);
  try {
    const nextDeck = await updateDeck(deck.id, {
      ...buildDeckUpsertRequestFromRecord(deck),
      is_public: !deck.is_public,
    });
    decks.value = decks.value.map((entry) => (entry.id === nextDeck.id ? nextDeck : entry));
    toast.success(nextDeck.is_public ? 'Deck is now public.' : 'Deck is now private.');
  } catch {
    toast.error('Unable to update deck visibility.');
  } finally {
    const nextSavingDeckIds = new Set(savingDeckIds.value);
    nextSavingDeckIds.delete(deck.id);
    savingDeckIds.value = nextSavingDeckIds;
  }
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
