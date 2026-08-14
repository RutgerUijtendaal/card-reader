<template>
  <section class="theme-panel-shell flex min-h-0 flex-col rounded-2xl p-5 shadow-sm">
    <div class="theme-divider flex flex-col gap-4 border-b pb-4 md:flex-row md:items-start md:justify-between">
      <div>
        <p class="theme-kicker text-xs font-medium uppercase tracking-[0.18em]">
          {{ isCreatingNew ? 'Create' : 'Edit' }} {{ kindItemLabel(selectedKind) }}
        </p>
        <h4 class="theme-section-title mt-2 text-lg font-semibold">
          {{ title }}
        </h4>
      </div>

      <div
        v-if="!isCreatingNew"
        class="theme-info-box text-xs"
      >
        <div class="theme-section-title font-semibold">
          Existing entry
        </div>
        <div class="mt-1">
          Key: <span class="font-mono text-[11px]">{{ editorEntry.key }}</span>
        </div>
      </div>
    </div>

    <div class="app-scrollbar mt-5 min-h-0 flex-1 space-y-5 overflow-y-auto pr-1">
      <CatalogEntryForm
        :kind="selectedKind"
        :entry="editorEntry"
        :advanced-open="true"
        :show-advanced-toggle="false"
        :key-disabled="!isCreatingNew"
        :uploading-asset="uploadingAsset"
        :detection-config-example="detectionConfigExample"
        :reference-assets-example="referenceAssetsExample"
        @update:entry="emit('update:entry', $event)"
        @upload-asset="emit('upload-asset')"
      />

      <div
        v-if="!isCreatingNew"
        class="theme-muted-panel"
      >
        <div class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]">
          {{ isDeckTagKind ? 'Linked decks' : 'Linked cards' }}
        </div>
        <div class="theme-section-muted mt-1 text-sm">
          {{ isDeckTagKind ? linkedDeckCount : linkedCardCount }}
          {{ isDeckTagKind ? 'decks' : 'cards' }} currently use this {{ kindItemLabel(selectedKind).toLowerCase() }}.
        </div>
        <div class="mt-4">
          <CatalogLinkedDecksGrid
            v-if="isDeckTagKind"
            :decks="linkedDecks"
            :empty-message="`No linked decks found for this ${kindItemLabel(selectedKind).toLowerCase()}.`"
          />
          <CatalogLinkedCardsGrid
            v-else
            :cards="linkedCards"
            :empty-message="`No linked cards found for this ${kindItemLabel(selectedKind).toLowerCase()}.`"
          />
        </div>
      </div>

      <div
        v-if="!isCreatingNew && classificationRules.length > 0"
        class="theme-muted-panel"
      >
        <div class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]">
          Classification rules
        </div>
        <p class="theme-section-muted mt-1 text-sm">
          This metadata entry can infer these pool-specific classifications.
        </p>
        <div class="mt-3 flex flex-wrap gap-2">
          <RouterLink
            v-for="rule in classificationRules"
            :key="rule.id"
            class="theme-pill theme-pill-accent hover:underline"
            :to="classificationRuleLocation(rule)"
          >
            {{ cardPoolLabel(rule.card_pool) }} · {{ rule.target_key }}
          </RouterLink>
        </div>
      </div>
    </div>

    <div class="theme-divider mt-5 flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
      <div class="theme-section-muted text-sm" />

      <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
        <button
          v-if="!isCreatingNew && selectedRow"
          class="btn-danger-secondary"
          type="button"
          :disabled="deletingEntryIds.has(selectedRow.id)"
          @click="emit('request-delete', selectedRow)"
        >
          {{ deletingEntryIds.has(selectedRow.id) ? 'Deleting...' : 'Delete' }}
        </button>
        <button
          class="btn-primary"
          type="button"
          :disabled="creatingEntry || savingCurrentEntry"
          @click="handlePrimaryAction"
        >
          {{ actionLabel }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { cardPoolLabel } from '@/domain/cards/cardPools';
import CatalogLinkedCardsGrid from '@/features/admin/components/CatalogLinkedCardsGrid.vue';
import CatalogLinkedDecksGrid from '@/features/admin/components/CatalogLinkedDecksGrid.vue';
import CatalogEntryForm from '@/features/admin/components/CatalogEntryForm.vue';
import type {
  CatalogFormEntry,
  CatalogKind,
  CatalogRow,
  LinkedCardPreview,
  LinkedDeckPreview,
  ClassificationRuleRecord,
} from '@/features/admin/types';

const props = withDefaults(defineProps<{
  selectedKind: CatalogKind;
  selectedRow: CatalogRow | null;
  isCreatingNew: boolean;
  editorEntry: CatalogFormEntry;
  creatingEntry: boolean;
  savingCurrentEntry: boolean;
  deletingEntryIds: Set<string>;
  uploadingAsset: boolean;
  detectionConfigExample: string;
  referenceAssetsExample: string;
  kindItemLabel: (kind: CatalogKind) => string;
  linkedCards: LinkedCardPreview[];
  linkedCardCount: number;
  linkedDecks?: LinkedDeckPreview[];
  linkedDeckCount?: number;
  classificationRules?: ClassificationRuleRecord[];
}>(), {
  linkedDecks: () => [],
  linkedDeckCount: 0,
  classificationRules: () => [],
});

const isDeckTagKind = computed(() => props.selectedKind === 'deck-roles' || props.selectedKind === 'deck-types');

const emit = defineEmits<{
  (e: 'create'): void;
  (e: 'save'): void;
  (e: 'create-new'): void;
  (e: 'upload-asset'): void;
  (e: 'update:entry', entry: CatalogFormEntry): void;
  (e: 'request-delete', entry: CatalogRow): void;
}>();

const title = computed(() => {
  if (props.isCreatingNew) {
    return `${props.kindItemLabel(props.selectedKind)} details`;
  }

  return props.selectedRow?.label || props.selectedRow?.key || 'Untitled entry';
});

const actionLabel = computed(() => {
  if (props.isCreatingNew) {
    return props.creatingEntry ? 'Creating...' : `Create ${props.kindItemLabel(props.selectedKind)}`;
  }

  return props.savingCurrentEntry ? 'Saving...' : 'Save Changes';
});

const handlePrimaryAction = (): void => {
  if (props.isCreatingNew) {
    emit('create');
    return;
  }

  emit('save');
};

const classificationRuleLocation = (rule: ClassificationRuleRecord) => ({
  path: '/admin',
  query: {
    admin_tab: 'catalog',
    admin_kind: rule.target_kind === 'role' ? 'card-roles' : 'card-factions',
    admin_entry: `${rule.target_kind}:${rule.target_key}`,
  },
});
</script>
