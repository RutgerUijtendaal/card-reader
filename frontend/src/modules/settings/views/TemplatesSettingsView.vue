<template>
  <div class="page-card flex min-h-0 flex-col space-y-4 xl:h-[calc(100vh-10rem)]">
    <h3 class="theme-section-title text-base font-semibold">
      Templates
    </h3>

    <div class="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
      <aside class="theme-panel-shell flex min-h-0 flex-col p-3">
        <div class="theme-divider mb-3 flex items-center justify-between border-b pb-3">
          <span class="theme-section-title text-sm font-semibold">Entries</span>
          <button
            class="btn-secondary px-3 py-2 text-xs"
            type="button"
            @click="startCreate"
          >
            New Template
          </button>
        </div>

        <div class="app-scrollbar min-h-0 flex-1 space-y-1 overflow-y-auto pr-1">
          <button
            v-for="item in templates"
            :key="item.id"
            class="w-full rounded-md border px-2 py-1.5 text-left text-sm"
            :class="
              selectedId === item.id
                ? 'theme-selected-surface'
                : 'theme-card-frame theme-section-title hover:-translate-y-0.5'
            "
            type="button"
            @click="selectTemplate(item.id)"
          >
            <div class="truncate font-medium">
              {{ item.label }}
            </div>
            <div class="theme-section-muted truncate text-xs">
              {{ item.key }}
            </div>
          </button>
          <p
            v-if="templates.length === 0"
            class="theme-section-muted text-xs"
          >
            No templates yet.
          </p>
        </div>
      </aside>

      <div class="theme-panel-shell flex min-h-0 flex-col p-4">
        <div class="app-scrollbar flex min-h-0 flex-1 flex-col overflow-y-auto pr-1">
          <div class="shrink-0 grid gap-3 md:grid-cols-2">
            <label class="field-label">
              Label
              <input
                v-model="form.label"
                class="input-base"
                placeholder="MTG Like V1"
              >
            </label>
            <label class="field-label">
              Key (optional)
              <input
                v-model="form.key"
                class="input-base"
                placeholder="mtg-like-v1"
              >
            </label>
          </div>

          <div class="mt-3 min-h-0 flex-1">
            <JsonEditorField
              v-model="form.definition_json"
              label="Definition JSON"
              hint="Define parser-driven regions with region_id, cut_region, parser_type, and ocr_config. Supported parser types: name_mana_cost, type_tag, rules_text, attack, health, affinity."
              min-height="20rem"
              fill-height
              example-title="Template Region Handler Example"
              :example-json="TEMPLATE_DEFINITION_EXAMPLE_JSON"
            />
          </div>
        </div>

        <div class="theme-divider mt-4 flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              class="btn-secondary"
              type="button"
              :disabled="saving"
              @click="resetForm"
            >
              Reset
            </button>
          </div>

          <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              v-if="!createMode"
              class="btn-danger-secondary"
              type="button"
              :disabled="saving || deleting"
              @click="openDeleteModal"
            >
              {{ deleting ? 'Deleting...' : 'Delete' }}
            </button>
            <button
              class="btn-primary"
              type="button"
              :disabled="saving"
              @click="saveTemplate"
            >
              {{ saving ? 'Saving...' : createMode ? 'Create Template' : 'Save Changes' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <ConfirmModal
    :open="deleteModalOpen"
    title="Delete Template"
    :message="`Delete template '${form.label || form.key}'?`"
    confirm-label="Delete"
    cancel-label="Cancel"
    :loading="deleting"
    loading-label="Deleting..."
    @cancel="deleteModalOpen = false"
    @confirm="confirmDelete"
  />
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { toast } from 'vue-sonner';
import ConfirmModal from '@/components/modals/ConfirmModal.vue';
import JsonEditorField from '@/modules/settings/components/JsonEditorField.vue';
import {
  createTemplate,
  deleteTemplate,
  fetchTemplates,
  updateTemplate,
} from '@/modules/settings/api/templates';
import type { TemplateDefinition, TemplateRecord } from '@/modules/settings/types';

type TemplateForm = {
  label: string;
  key: string;
  definition_json: string;
};

const TEMPLATE_DEFINITION_EXAMPLE: TemplateDefinition = {
  id: 'mtg-like-v1',
  version: 7,
  regions: [
    {
      region_id: 'top_bar',
      parser_type: 'name_mana_cost',
      cut_region: {
        unit: 'relative',
        x: 0.04,
        y: 0.02,
        w: 0.92,
        h: 0.07,
      },
      ocr_config: {
        ocr_min_confidence: 0.55,
      },
    },
    {
      region_id: 'type_bar',
      parser_type: 'type_tag',
      cut_region: {
        unit: 'relative',
        x: 0.04,
        y: 0.54,
        w: 0.92,
        h: 0.05,
      },
      ocr_config: {},
    },
    {
      region_id: 'rules_text',
      parser_type: 'rules_text',
      cut_region: {
        unit: 'relative',
        x: 0.07,
        y: 0.6,
        w: 0.86,
        h: 0.32,
      },
      ocr_config: {},
    },
    {
      region_id: 'rules_text_fallback',
      parser_type: 'rules_text',
      cut_region: {
        unit: 'relative',
        x: 0.07,
        y: 0.7,
        w: 0.86,
        h: 0.12,
      },
      ocr_config: {},
    },
    {
      region_id: 'bottom_left',
      parser_type: 'attack',
      cut_region: {
        unit: 'relative',
        x: 0.01,
        y: 0.9,
        w: 0.14,
        h: 0.09,
      },
      ocr_config: {},
    },
    {
      region_id: 'bottom_middle',
      parser_type: 'affinity',
      cut_region: {
        unit: 'relative',
        x: 0.37,
        y: 0.93,
        w: 0.26,
        h: 0.06,
      },
      ocr_config: {},
    },
    {
      region_id: 'bottom_right',
      parser_type: 'health',
      cut_region: {
        unit: 'relative',
        x: 0.85,
        y: 0.9,
        w: 0.14,
        h: 0.08,
      },
      ocr_config: {},
    },
  ],
};

const TEMPLATE_DEFINITION_EXAMPLE_JSON = JSON.stringify(TEMPLATE_DEFINITION_EXAMPLE, null, 2);

const templates = ref<TemplateRecord[]>([]);
const selectedId = ref<string | null>(null);
const saving = ref(false);
const deleting = ref(false);
const deleteModalOpen = ref(false);

const form = reactive<TemplateForm>({
  label: '',
  key: '',
  definition_json: TEMPLATE_DEFINITION_EXAMPLE_JSON,
});

const createMode = computed(() => selectedId.value === null);

const loadTemplates = async (): Promise<void> => {
  const rows = await fetchTemplates();
  templates.value = rows;
  if (rows.length === 0) {
    selectedId.value = null;
    resetForm();
    return;
  }
  if (selectedId.value && rows.some((row) => row.id === selectedId.value)) {
    selectTemplate(selectedId.value);
    return;
  }
  selectTemplate(rows[0].id);
};

const selectTemplate = (id: string): void => {
  const row = templates.value.find((item) => item.id === id);
  if (!row) return;
  selectedId.value = row.id;
  form.label = row.label;
  form.key = row.key;
  form.definition_json = formatJsonForEditor(row.definition_json);
};

const startCreate = (): void => {
  selectedId.value = null;
  resetForm();
};

const resetForm = (): void => {
  if (selectedId.value) {
    selectTemplate(selectedId.value);
    return;
  }
  form.label = '';
  form.key = '';
  form.definition_json = TEMPLATE_DEFINITION_EXAMPLE_JSON;
};

const saveTemplate = async (): Promise<void> => {
  if (saving.value) return;
  const normalizedLabel = form.label.trim();
  if (!normalizedLabel) {
    toast.error('Label is required.');
    return;
  }

  const normalizedDefinition = normalizeDefinitionJson(form.definition_json);
  if (!normalizedDefinition.ok) {
    toast.error(normalizedDefinition.message);
    return;
  }

  saving.value = true;
  try {
    const payload = {
      label: normalizedLabel,
      key: form.key.trim() || undefined,
      definition_json: normalizedDefinition.value,
    };
    if (createMode.value) {
      await createTemplate(payload);
      toast.success('Template created.');
    } else if (selectedId.value) {
      await updateTemplate(selectedId.value, payload);
      toast.success('Template updated.');
    }
    await loadTemplates();
  } catch (error) {
    console.error('Save template failed', error);
    toast.error(extractErrorMessage(error, 'Failed to save template.'));
  } finally {
    saving.value = false;
  }
};

const openDeleteModal = (): void => {
  if (createMode.value) return;
  deleteModalOpen.value = true;
};

const confirmDelete = async (): Promise<void> => {
  if (!selectedId.value || deleting.value) return;
  deleting.value = true;
  try {
    await deleteTemplate(selectedId.value);
    deleteModalOpen.value = false;
    toast.success('Template deleted.');
    selectedId.value = null;
    await loadTemplates();
  } catch (error) {
    console.error('Delete template failed', error);
    toast.error(extractErrorMessage(error, 'Failed to delete template.'));
  } finally {
    deleting.value = false;
  }
};

const normalizeDefinitionJson = (
  raw: string,
): { ok: true; value: TemplateDefinition } | { ok: false; message: string } => {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { ok: false, message: 'Definition JSON is required.' };
  }
  try {
    const parsed = JSON.parse(trimmed);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      return { ok: false, message: 'Definition JSON must be an object.' };
    }
    return { ok: true, value: parsed as TemplateDefinition };
  } catch {
    return { ok: false, message: 'Definition JSON must be valid JSON.' };
  }
};

const formatJsonForEditor = (raw: string): string => {
  const trimmed = raw.trim();
  if (!trimmed) {
    return '{}';
  }

  try {
    return JSON.stringify(JSON.parse(trimmed), null, 2);
  } catch {
    return raw;
  }
};

const extractErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const maybeResponse = (error as { response?: { data?: { detail?: unknown } } }).response;
    const detail = maybeResponse?.data?.detail;
    if (typeof detail === 'string' && detail.length > 0) return detail;
  }
  if (typeof error === 'object' && error && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return fallback;
};

onMounted(() => {
  void loadTemplates();
});
</script>
