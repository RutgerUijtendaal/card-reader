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
      query: {
        ...filterQuery,
        return_to: staff ? 'staff_encounters' : mine ? 'my_encounters' : 'encounters',
      },
    }"
    :variant="owned ? 'owned' : 'browse'"
  >
    <template #badge>
      <span
        class="theme-art-chip gap-1.5 px-2 py-0.5 text-xs"
        data-testid="encounter-tile-badge"
      >
        <span
          v-if="owned"
          class="h-1.5 w-1.5 rounded-full"
          :style="{ background: visibilityDotColor }"
          aria-hidden="true"
        />
        {{ owned ? visibilityLabel : encounter.creator.username }}
      </span>
      <span
        v-if="encounter.is_official"
        class="theme-art-chip px-2 py-0.5 text-xs"
      >Official</span>
    </template>
    <template
      v-if="encounter.can_edit"
      #actions
    >
      <RouterLink
        class="theme-art-chip h-8 w-8"
        :to="`/my/encounters/${encounter.id}/edit`"
        aria-label="Edit Encounter"
        title="Edit Encounter"
      >
        <Pencil class="h-4 w-4" />
      </RouterLink>
    </template>
    <template
      v-if="(showFactions && encounter.factions.length > 0) || (owned && !encounter.status.is_valid)"
      #tags
    >
      <div class="flex flex-wrap items-center gap-1.5">
        <span
          v-for="faction in showFactions ? encounter.factions : []"
          :key="faction"
          class="theme-pill theme-pill-neutral text-xs"
        >{{ cardFactionLabel(faction) }}</span>
        <span
          v-if="owned && !encounter.status.is_valid"
          class="theme-pill theme-pill-warning text-xs"
        >Under construction</span>
      </div>
    </template>
    <template #footer>
      <span class="collection-tile-footer-items">
        <span class="collection-tile-footer-item">{{ encounter.total_cards }} cards</span>
        <span
          v-if="encounter.sideboard_count > 0"
          class="collection-tile-footer-item"
        >{{ encounter.sideboard_count }} sideboard{{ encounter.sideboard_count === 1 ? '' : 's' }}</span>
        <span
          v-if="staff"
          class="collection-tile-footer-item"
        >{{ encounter.creator.username }}</span>
      </span>
      <span
        v-if="owned"
        class="collection-tile-footer-end"
      >Updated {{ updatedDate }}</span>
    </template>
  </CollectionListCard>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, type LocationQueryRaw } from 'vue-router';
import { Pencil } from 'lucide-vue-next';
import type { EncounterSummary } from '@/domain/encounters/types';
import { cardFactionLabel } from '@/domain/cards/cardFactions';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import CollectionListCard from '@/shared/components/CollectionListCard.vue';
const props = withDefaults(
  defineProps<{
    encounter: EncounterSummary;
    staff: boolean;
    mine: boolean;
    filterQuery: LocationQueryRaw;
    /** Off inside a single-faction section, whose heading already names the faction. */
    showFactions?: boolean;
  }>(),
  { showFactions: true },
);
const owned = computed(() => props.staff || props.mine);
const updatedDate = computed(() =>
  new Date(props.encounter.updated_at).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  }),
);
const visibilityLabel = computed(
  () =>
    props.encounter.visibility.charAt(0).toUpperCase() + props.encounter.visibility.slice(1),
);
const VISIBILITY_DOT_COLORS: Record<EncounterSummary['visibility'], string> = {
  private: 'var(--color-nav-text)',
  unlisted: 'var(--color-pill-warning-text)',
  public: 'var(--color-pill-success-text)',
};
const visibilityDotColor = computed(() => VISIBILITY_DOT_COLORS[props.encounter.visibility]);
</script>
