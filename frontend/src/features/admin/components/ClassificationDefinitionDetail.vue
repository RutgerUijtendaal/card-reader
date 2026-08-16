<template>
  <section class="theme-panel-shell flex min-h-0 flex-col rounded-2xl p-5 shadow-sm">
    <div
      v-if="!definition"
      class="theme-section-muted py-8 text-sm"
    >
      Select a card classification value to inspect its inference rules.
    </div>
    <template v-else>
      <div class="theme-divider border-b pb-4">
        <p class="theme-kicker text-xs font-medium uppercase tracking-[0.18em]">
          {{ definition.target_kind === 'role' ? 'Card Role' : definition.target_kind === 'faction' ? 'Card Faction' : 'Mana Family' }}
        </p>
        <h4 class="theme-section-title mt-2 text-lg font-semibold">
          {{ definition.label }}
        </h4>
        <p class="theme-section-muted mt-2 text-sm">
          <template v-if="definition.derived">
            This is a derived empty state. It cannot receive inference rules.
          </template>
          <template v-else>
            Automatic imports union every enabled Tag, Type, or Symbol rule matching the selected pool.
          </template>
        </p>
      </div>

      <div class="app-scrollbar mt-5 min-h-0 flex-1 space-y-5 overflow-y-auto pr-1">
        <div class="grid gap-3 sm:grid-cols-3">
          <div
            v-for="pool in CARD_POOL_OPTIONS"
            :key="pool.value"
            class="theme-muted-panel"
          >
            <div class="theme-section-title text-sm font-semibold">
              {{ pool.label }}
            </div>
            <div class="theme-section-muted mt-1 text-xs">
              {{ definition.linked_card_counts[pool.value] ?? 0 }} linked cards ·
              {{ ruleCount(pool.value) }} rules
            </div>
          </div>
        </div>

        <div
          v-if="!definition.derived"
          class="space-y-5"
        >
          <section
            v-for="pool in CARD_POOL_OPTIONS"
            :key="pool.value"
            class="theme-muted-panel space-y-3"
          >
            <div class="flex items-center justify-between gap-3">
              <h5 class="theme-section-title text-sm font-semibold">
                {{ pool.label }}
              </h5>
              <span class="theme-pill theme-pill-accent">{{ rulesForPool(pool.value).length }}</span>
            </div>
            <div
              v-if="rulesForPool(pool.value).length === 0"
              class="theme-section-muted text-sm"
            >
              No rules configured.
            </div>
            <div
              v-for="rule in rulesForPool(pool.value)"
              :key="rule.id"
              class="theme-card-frame grid gap-3 rounded-xl p-3 md:grid-cols-[auto_minmax(0,1fr)_auto_auto] md:items-center"
            >
              <span
                class="theme-pill"
                :class="rule.source_kind === 'tag' ? 'theme-pill-success' : rule.source_kind === 'type' ? 'theme-pill-warning' : 'theme-pill-neutral'"
              >
                {{ rule.source_kind }}
              </span>
              <AppSelect
                :model-value="rule.source_id"
                :options="sourceOptions(rule.source_kind)"
                :disabled="savingRuleIds.has(rule.id)"
                @update:model-value="updateSource(rule, String($event ?? ''))"
              />
              <label class="theme-section-title inline-flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  :checked="rule.enabled"
                  :disabled="savingRuleIds.has(rule.id)"
                  @change="setEnabled(rule, ($event.target as HTMLInputElement).checked)"
                >
                Enabled
              </label>
              <button
                class="btn-danger-secondary px-3 py-2 text-xs"
                type="button"
                :disabled="savingRuleIds.has(rule.id)"
                @click="removeRule(rule)"
              >
                Remove
              </button>
            </div>
          </section>

          <section class="theme-info-box space-y-3">
            <h5 class="theme-section-title text-sm font-semibold">
              Add inference rule
            </h5>
            <div class="grid gap-3 md:grid-cols-3">
              <label class="field-label">
                Pool
                <AppSelect
                  v-model="newRule.card_pool"
                  :options="CARD_POOL_OPTIONS"
                />
              </label>
              <label class="field-label">
                Source kind
                <AppSelect
                  v-model="newRule.source_kind"
                  :options="SOURCE_KIND_OPTIONS"
                  @change="resetSource"
                />
              </label>
              <label class="field-label">
                Existing source
                <AppSelect
                  v-model="newRule.source_id"
                  :options="sourceOptions(newRule.source_kind)"
                  placeholder="Select a source"
                />
              </label>
            </div>
            <button
              class="btn-primary"
              type="button"
              :disabled="creating || !newRule.source_id"
              @click="addRule"
            >
              {{ creating ? 'Adding...' : 'Add Rule' }}
            </button>
          </section>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import AppSelect from '@/shared/components/app/AppSelect.vue';
import { CARD_POOL_OPTIONS, type CardPool } from '@/domain/cards/cardPools';
import {
  createClassificationRule,
  deleteClassificationRule,
  updateClassificationRule,
} from '@/features/admin/api/catalog';
import { extractErrorMessage } from '@/features/admin/utils/catalogAdmin';
import type {
  ClassificationDefinitionRecord,
  ClassificationRuleRecord,
  ClassificationSourceKind,
  TagRecord,
  TypeRecord,
  SymbolRecord,
} from '@/features/admin/types';

const props = defineProps<{
  definition: ClassificationDefinitionRecord | null;
  tags: TagRecord[];
  types: TypeRecord[];
  symbols: SymbolRecord[];
}>();

const emit = defineEmits<{ (event: 'changed'): void }>();
const SOURCE_KIND_OPTIONS = [
  { value: 'tag', label: 'Tag' },
  { value: 'type', label: 'Type' },
  { value: 'symbol', label: 'Symbol' },
] as const;
const creating = ref(false);
const savingRuleIds = ref(new Set<string>());
const newRule = reactive<{
  card_pool: CardPool;
  source_kind: ClassificationSourceKind;
  source_id: string;
}>({ card_pool: 'player', source_kind: 'tag', source_id: '' });

watch(() => props.definition?.id, () => {
  newRule.source_id = '';
});

const sourceOptions = (kind: ClassificationSourceKind) =>
  (kind === 'tag' ? props.tags : kind === 'type' ? props.types : props.symbols).map((row) => ({
    value: row.id,
    label: `${row.label} (${row.key})`,
  }));

const rulesForPool = (pool: CardPool): ClassificationRuleRecord[] =>
  props.definition?.rules.filter((rule) => rule.card_pool === pool) ?? [];

const ruleCount = (pool: CardPool): number => {
  const counts = props.definition?.rule_counts[pool];
  return (counts?.tag ?? 0) + (counts?.type ?? 0) + (counts?.symbol ?? 0);
};

const withRuleMutation = async (ruleId: string, mutation: () => Promise<void>): Promise<void> => {
  savingRuleIds.value = new Set(savingRuleIds.value).add(ruleId);
  try {
    await mutation();
    emit('changed');
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to update classification rule.'));
  } finally {
    const next = new Set(savingRuleIds.value);
    next.delete(ruleId);
    savingRuleIds.value = next;
  }
};

const updateSource = (rule: ClassificationRuleRecord, sourceId: string): void => {
  if (!sourceId || sourceId === rule.source_id) return;
  void withRuleMutation(rule.id, async () => {
    await updateClassificationRule(rule.id, { source_id: sourceId });
    toast.success('Classification rule updated.');
  });
};

const setEnabled = (rule: ClassificationRuleRecord, enabled: boolean): void => {
  void withRuleMutation(rule.id, async () => {
    await updateClassificationRule(rule.id, { enabled });
    toast.success(enabled ? 'Classification rule enabled.' : 'Classification rule disabled.');
  });
};

const removeRule = (rule: ClassificationRuleRecord): void => {
  void withRuleMutation(rule.id, async () => {
    await deleteClassificationRule(rule.id);
    toast.success('Classification rule removed.');
  });
};

const resetSource = (): void => {
  newRule.source_id = '';
};

const addRule = async (): Promise<void> => {
  if (!props.definition || props.definition.derived || !newRule.source_id || creating.value) return;
  creating.value = true;
  try {
    await createClassificationRule({
      card_pool: newRule.card_pool,
      target_kind: props.definition.target_kind,
      target_key: props.definition.key,
      source_kind: newRule.source_kind,
      source_id: newRule.source_id,
      enabled: true,
    });
    newRule.source_id = '';
    toast.success('Classification rule added.');
    emit('changed');
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to add classification rule.'));
  } finally {
    creating.value = false;
  }
};
</script>
