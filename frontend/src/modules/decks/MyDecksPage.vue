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
        to="/my/decks/new"
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
      class="grid gap-4"
    >
      <DeckListCard
        v-for="deck in decks"
        :key="deck.id"
        :deck="deck"
        mode="owned"
      >
        <template #actions>
          <RouterLink
            v-if="deck.is_public"
            class="btn-secondary"
            :to="`/decks/${deck.id}`"
          >
            Open
          </RouterLink>
          <RouterLink
            class="btn-secondary"
            :to="`/my/decks/${deck.id}/edit`"
          >
            Edit
          </RouterLink>
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
import { deleteDeck, fetchMyDecks } from '@/modules/decks/api';
import DeckListCard from '@/modules/decks/components/DeckListCard.vue';
import type { DeckRecord } from '@/modules/decks/types';

const decks = ref<DeckRecord[]>([]);
const loading = ref(false);
const deleting = ref(false);
const deleteTarget = ref<DeckRecord | null>(null);

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
