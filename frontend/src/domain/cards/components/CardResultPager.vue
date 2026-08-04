<template>
  <nav
    v-if="visible"
    class="theme-divider flex flex-col gap-3 border-b pb-4 sm:flex-row sm:items-center sm:justify-between"
    aria-label="Card result navigation"
  >
    <span class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]">
      {{ positionLabel }}
    </span>
    <div class="flex flex-wrap gap-2">
      <button
        class="btn-secondary inline-flex items-center gap-2"
        type="button"
        :disabled="!previousCardId"
        @click="$emit('previous')"
      >
        <ChevronLeft class="h-4 w-4" />
        <span>Previous Card</span>
      </button>
      <button
        class="btn-secondary inline-flex items-center gap-2"
        type="button"
        :disabled="!nextCardId && !hasMoreResults"
        @click="$emit('next')"
      >
        <span>{{ isLoadingMoreCards ? 'Loading Next...' : 'Next Card' }}</span>
        <ChevronRight class="h-4 w-4" />
      </button>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ChevronLeft, ChevronRight } from 'lucide-vue-next';

defineProps<{
  visible: boolean;
  positionLabel: string;
  previousCardId: string | null;
  nextCardId: string | null;
  hasMoreResults: boolean;
  isLoadingMoreCards: boolean;
}>();

defineEmits<{
  previous: [];
  next: [];
}>();
</script>
