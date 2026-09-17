<template>
  <article
    class="theme-divider grid gap-4 border-b py-5 sm:grid-cols-[5rem_minmax(0,1fr)]"
    :aria-label="row.file.name"
  >
    <div class="theme-card-image-well aspect-[63/88] w-20 overflow-hidden rounded-lg">
      <img
        v-if="!previewUnavailable"
        :src="row.previewUrl"
        :alt="row.file.name"
        class="h-full w-full object-contain"
        loading="lazy"
        @error="previewUnavailable = true"
      >
      <p
        v-else
        class="theme-section-muted p-2 text-center text-xs"
      >
        Preview unavailable. The image will be checked on import.
      </p>
    </div>
    <div class="min-w-0 space-y-3">
      <div class="flex items-start justify-between gap-3">
        <p class="theme-section-muted break-all text-xs">
          {{ row.file.name }}
        </p>
        <button
          v-if="editable"
          type="button"
          class="btn-secondary text-xs"
          :disabled="disabled"
          @click="emit('remove')"
        >
          Remove
        </button>
      </div>
      <label class="field-label">
        Label
        <input
          class="input-base"
          :value="row.label"
          required
          :disabled="disabled || !editable"
          @input="emit('label', ($event.target as HTMLInputElement).value)"
        >
      </label>
      <template v-if="editable">
        <CardSearchSelect
          :key="row.selection.kind === 'selected' ? row.selection.hero.id : row.selection.kind"
          label="Optional hero"
          placeholder="Search heroes…"
          :candidates="heroes"
          :disabled="disabled || !heroesReady"
          :disabled-card-ids="disabledHeroIds"
          disabled-action-label="Already selected"
          @select="emit('hero', $event.id)"
        />
        <div
          v-if="row.selection.kind === 'selected'"
          class="flex items-center gap-3"
        >
          <img
            v-if="row.selection.hero.image_url"
            :src="toAbsoluteApiUrl(row.selection.hero.image_url)"
            :alt="row.selection.hero.name"
            class="w-12 rounded"
          >
          <div class="min-w-0 text-sm">
            <p class="theme-section-title font-medium">
              {{ row.selection.hero.name }}
            </p>
            <p class="theme-section-muted">
              {{ row.selection.hero.card_pool }} · {{ factionDescription }}
            </p>
          </div>
        </div>
        <button
          v-if="row.selection.kind !== 'none'"
          class="btn-secondary text-xs"
          type="button"
          :disabled="disabled"
          @click="emit('hero', null)"
        >
          Library only
        </button>
        <p
          v-else
          class="theme-section-muted text-sm"
        >
          Library only — no hero assignment.
        </p>
        <div
          v-if="suggestion && row.selection.kind === 'none'"
          class="theme-muted-panel flex flex-wrap items-center gap-2 p-3 text-sm"
        >
          <span>Suggested: {{ suggestion.name }} ({{ suggestion.card_pool }})</span>
          <button
            class="btn-secondary"
            type="button"
            :disabled="disabled || disabledHeroIds.includes(suggestion.id)"
            @click="emit('hero', suggestion.id)"
          >
            Use this hero
          </button>
        </div>
        <div
          v-if="row.selection.kind === 'selected' && row.selection.hero.card_back_override_id"
          class="theme-muted-panel space-y-3 p-3"
        >
          <div class="flex items-center gap-3">
            <img
              v-if="row.selection.hero.effective_card_back?.asset.image_url"
              :src="toAbsoluteApiUrl(row.selection.hero.effective_card_back.asset.image_url)"
              alt="Current hero override"
              class="w-10 rounded"
            >
            <p class="text-sm">
              Current override: {{ row.selection.hero.effective_card_back?.asset.label ?? 'Unavailable image' }}
            </p>
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              :checked="row.selection.replacementConfirmed"
              :disabled="disabled"
              @change="emit('confirm', ($event.target as HTMLInputElement).checked)"
            >
            Replace this hero’s override. Keep the old back in the library.
          </label>
        </div>
        <p
          v-if="error"
          class="theme-alert-danger text-sm"
          role="alert"
        >
          {{ error }}
        </p>
      </template>
      <div
        aria-live="polite"
        class="text-sm"
      >
        <p
          v-if="row.state.kind === 'submitting'"
          class="theme-section-muted"
        >
          Importing…
        </p>
        <p
          v-else-if="row.state.kind === 'succeeded'"
          class="theme-section-title"
        >
          Imported{{ row.state.result.hero_card_id ? ' and assigned to hero' : ' to library' }}.
          <span v-if="row.selection.kind === 'selected'">{{ row.selection.hero.name }}</span>
        </p>
        <p
          v-else-if="row.state.kind === 'rejected' || row.state.kind === 'deleted'"
          class="theme-alert-danger"
        >
          {{ row.state.message }}
        </p>
        <div
          v-else-if="row.state.kind === 'uncertain'"
          class="theme-alert-danger space-y-2"
        >
          <p>Completion is not yet confirmed. Keep this page open and check or retry this same import.</p>
          <button
            type="button"
            class="btn-secondary"
            :disabled="disabled"
            @click="emit('retry')"
          >
            Check / retry
          </button>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import CardSearchSelect from '@/domain/cards/components/CardSearchSelect.vue';
import type { CardListItem } from '@/domain/cards/types';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import { cardFactionLabel } from '@/domain/cards/cardFactions';
import { isEditableRow, type CardBackImportRow } from '@/features/admin/composables/useCardBackImport';
import { suggestHero } from '@/features/admin/utils/cardBackImport';

const props = defineProps<{
  row: CardBackImportRow; heroes: CardListItem[]; heroesReady: boolean;
  disabledHeroIds: string[]; disabled: boolean; error: string;
}>();
const emit = defineEmits<{
  remove: []; label: [value: string]; hero: [id: string | null]; confirm: [value: boolean]; retry: [];
}>();
const editable = computed(() => isEditableRow(props.row));
const previewUnavailable = ref(false);
const suggestion = computed(() => props.heroesReady ? suggestHero(props.row.file.name, props.heroes) : null);
const factionDescription = computed(() => props.row.selection.kind === 'selected'
  ? props.row.selection.hero.card_factions?.map(cardFactionLabel).join(', ') || 'No faction' : '');
</script>
