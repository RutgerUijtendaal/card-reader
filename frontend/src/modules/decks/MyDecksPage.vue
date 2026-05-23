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
      <div
        v-for="deck in decks"
        :key="deck.id"
        class="page-card flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"
      >
        <div class="flex min-w-0 gap-4">
          <div class="theme-card-frame-muted theme-card-image-well flex h-32 w-24 shrink-0 items-center justify-center rounded-xl">
            <img
              v-if="deck.hero_card.image_url"
              :src="toAbsoluteApiUrl(deck.hero_card.image_url)"
              :alt="deck.hero_card.name"
              class="h-full w-full object-contain"
            >
            <div
              v-else
              class="theme-kicker text-xs"
            >
              No image
            </div>
          </div>

          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="theme-section-title text-lg font-semibold">
                {{ deck.name }}
              </h3>
              <span
                class="theme-pill text-xs"
                :class="deck.is_public ? 'theme-pill-accent' : 'theme-pill-neutral'"
              >
                {{ deck.is_public ? 'Public' : 'Private' }}
              </span>
            </div>
            <div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              <span class="theme-section-muted">
                <span class="theme-section-title font-medium">Cards</span>
                {{ deck.mainboard.total_cards }} / 60
              </span>
              <span class="theme-section-muted">
                <span class="theme-section-title font-medium">Unique</span>
                {{ deck.mainboard.unique_cards }}
              </span>
              <span class="theme-section-muted">
                <span class="theme-section-title font-medium">Status</span>
                {{ deck.status.label }}
              </span>
            </div>
            <p class="theme-section-muted mt-1 text-sm">
              Hero: {{ deck.hero_card.name }}
            </p>
            <p
              v-if="deck.status.issues.length > 0"
              class="theme-section-muted mt-1 text-sm"
            >
              {{ deck.status.issues[0] }}
            </p>
            <p
              v-if="deck.description"
              class="theme-section-title mt-2 text-sm"
            >
              {{ deck.description }}
            </p>
          </div>
        </div>

        <div class="flex flex-wrap gap-2">
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
        </div>
      </div>
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
import { toAbsoluteApiUrl } from '@/api/client';
import ConfirmModal from '@/components/modals/ConfirmModal.vue';
import { deleteDeck, fetchMyDecks } from '@/modules/decks/api';
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
