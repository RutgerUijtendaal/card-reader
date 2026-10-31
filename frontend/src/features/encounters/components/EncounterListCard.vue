<template>
  <CollectionListCard
    :title="encounter.name || 'Untitled Encounter'"
    :description="encounter.description"
    :image-url="
      encounter.boss_card?.image_url ? toAbsoluteApiUrl(encounter.boss_card.image_url) : null
    "
    :image-alt="encounter.boss_card?.name || ''"
    :to="{
      path: `/encounters/${encounter.id}`,
      query: { return_to: staff ? 'staff_encounters' : 'encounters' },
    }"
    :variant="staff ? 'owned' : 'browse'"
  >
    <template #badge>
      <span
        class="theme-pill shrink-0 text-xs"
        :class="
          staff && encounter.visibility === 'public' ? 'theme-pill-success' : 'theme-pill-neutral'
        "
      >
        {{
          staff
            ? encounter.visibility === 'public'
              ? 'Public'
              : 'Staff only'
            : encounter.creator.username
        }}
      </span>
    </template>
    <template
      v-if="canEdit"
      #actions
    >
      <RouterLink
        class="btn-secondary"
        :to="`/staff/encounters/${encounter.id}/edit`"
        aria-label="Edit Encounter"
      >
        <Pencil class="h-4 w-4" /> Edit
      </RouterLink>
    </template>
    <template #tags>
      <div class="flex flex-wrap items-center gap-1.5">
        <span
          v-for="faction in encounter.factions"
          :key="faction"
          class="theme-pill theme-pill-neutral text-xs"
        >{{ cardFactionLabel(faction) }}</span>
        <span
          v-if="staff && !encounter.status.is_valid"
          class="theme-pill theme-pill-warning text-xs"
        >Under construction</span>
      </div>
    </template>
    <template #footer>
      <div class="collection-list-card-footer-meta theme-section-muted text-xs">
        <span class="collection-list-card-footer-meta-item"><Crown class="h-4 w-4" />{{ encounter.boss_card?.name || 'No boss selected' }}</span>
        <span class="collection-list-card-footer-meta-item"><LibraryBig class="h-4 w-4" />Maindeck {{ encounter.total_cards }}</span>
        <span class="collection-list-card-footer-meta-item"><PanelRight class="h-4 w-4" />Sideboards {{ encounter.sideboard_count }}</span>
        <span
          v-if="staff"
          class="collection-list-card-footer-meta-item"
        ><UserRound class="h-4 w-4" />{{ encounter.creator.username }}</span>
        <span class="collection-list-card-footer-meta-item"><CalendarDays class="h-4 w-4" />Updated {{ updatedDate }}</span>
      </div>
    </template>
  </CollectionListCard>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { CalendarDays, Crown, LibraryBig, PanelRight, Pencil, UserRound } from 'lucide-vue-next';
import type { EncounterSummary } from '@/domain/encounters/types';
import { cardFactionLabel } from '@/domain/cards/cardFactions';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import CollectionListCard from '@/shared/components/CollectionListCard.vue';
const props = defineProps<{ encounter: EncounterSummary; staff: boolean; canEdit: boolean }>();
const updatedDate = computed(() => {
  const date = new Date(props.encounter.updated_at);
  return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()}`;
});
</script>
