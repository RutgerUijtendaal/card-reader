<template>
  <fieldset
    :disabled="editor.locked.value"
    class="mx-auto w-full max-w-4xl space-y-9 pb-8"
  >
    <CardBuilderDetailsFields
      :name="editor.form.name"
      :summary="editor.form.description_markup"
      :long-description="editor.form.long_description_markup"
      kind="Encounter"
      field-prefix="encounter"
      pool="evil"
      description="Give your Encounter a clear identity and describe how it plays."
      @update:name="editor.setDetails({ name: $event })"
      @update:summary="editor.setDetails({ description_markup: $event })"
      @update:long-description="editor.setDetails({ long_description_markup: $event })"
    />
    <section class="space-y-5">
      <div class="space-y-1">
        <h2 class="theme-section-title text-lg font-semibold">
          Organization
        </h2>
        <p class="theme-section-muted text-sm">
          Classify your Encounter and control how it appears to players.
        </p>
      </div>
      <AppFormSection
        title="Faction tags"
        description="Choose the factions used to organize this Encounter."
      >
        <div class="flex flex-wrap gap-2">
          <ChoicePill
            v-for="option in CARD_FACTION_OPTIONS"
            :key="option.value"
            :selected="editor.form.factions.includes(option.value)"
            @click="toggleFaction(option.value)"
          >
            {{ option.label }}
          </ChoicePill>
        </div>
      </AppFormSection>
      <AppFormSection
        title="Visibility"
        :description="
          editor.form.visibility === 'public'
            ? 'Visible to everyone when this Encounter is valid.'
            : 'Visible to all staff, including unfinished work.'
        "
      >
        <div class="flex flex-wrap gap-2">
          <ChoicePill
            :selected="editor.form.visibility === 'private'"
            @click="editor.setDetails({ visibility: 'private' })"
          >
            Staff only
          </ChoicePill><ChoicePill
            :selected="editor.form.visibility === 'public'"
            @click="editor.setDetails({ visibility: 'public' })"
          >
            Public
          </ChoicePill>
        </div>
      </AppFormSection>
    </section>
    <div class="theme-divider flex justify-end border-t pt-6">
      <button
        class="btn-primary"
        type="button"
        @click="editor.setMode('cards')"
      >
        <span>Continue to Cards</span><ArrowRight class="h-4 w-4" />
      </button>
    </div>
  </fieldset>
</template>
<script setup lang="ts">
import { ArrowRight } from 'lucide-vue-next';
import CardBuilderDetailsFields from '@/domain/cards/components/CardBuilderDetailsFields.vue';
import { CARD_FACTION_OPTIONS, type CardFaction } from '@/domain/cards/cardFactions';
import AppFormSection from '@/shared/components/app/AppFormSection.vue';
import ChoicePill from '@/shared/components/ChoicePill.vue';
import type { useEncounterEditor } from '../composables/useEncounterEditor';
const props = defineProps<{ editor: ReturnType<typeof useEncounterEditor> }>();
const toggleFaction = (value: CardFaction) => {
  const form = props.editor.form;
  props.editor.setDetails({
    factions: form.factions.includes(value)
      ? form.factions.filter((item) => item !== value)
      : [...form.factions, value],
  });
};
</script>
