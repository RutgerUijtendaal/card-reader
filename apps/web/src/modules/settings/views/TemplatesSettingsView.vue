<template>
  <div class="page-card space-y-4">
    <h3 class="text-base font-semibold text-slate-800">Templates</h3>
    <p class="text-sm text-slate-600">Manage parser templates as JSON definitions.</p>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
      <aside class="rounded-lg border border-slate-200 p-3">
        <div class="mb-3 flex items-center justify-between">
          <span class="text-sm font-semibold text-slate-800">Entries</span>
          <button class="btn-secondary px-2 py-1 text-xs" type="button" @click="startCreate">
            New
          </button>
        </div>

        <div class="space-y-1">
          <button
            v-for="item in templates"
            :key="item.id"
            class="w-full rounded-md border px-2 py-1.5 text-left text-sm"
            :class="
              selectedId === item.id
                ? 'border-sky-300 bg-sky-50 text-sky-700'
                : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            "
            type="button"
            @click="selectTemplate(item.id)"
          >
            <div class="truncate font-medium">{{ item.label }}</div>
            <div class="truncate text-xs text-slate-500">{{ item.key }}</div>
          </button>
          <p v-if="templates.length === 0" class="text-xs text-slate-500">No templates yet.</p>
        </div>
      </aside>

      <div class="rounded-lg border border-slate-200 p-4">
        <div class="grid gap-3 md:grid-cols-2">
          <label class="field-label">
            Label
            <input v-model="form.label" class="input-base" placeholder="MTG Like V1" />
          </label>
          <label class="field-label">
            Key (optional)
            <input v-model="form.key" class="input-base" placeholder="mtg-like-v1" />
          </label>
        </div>

        <label class="field-label mt-3">
          Definition JSON
          <textarea
            v-model="form.definition_json"
            class="input-base min-h-[320px] font-mono text-xs"
            spellcheck="false"
          />
        </label>

        <div class="mt-4 flex flex-wrap gap-2">
          <button class="btn-primary" type="button" :disabled="saving" @click="saveTemplate">
            {{ saving ? 'Saving...' : createMode ? 'Create Template' : 'Save Changes' }}
          </button>
          <button class="btn-secondary" type="button" :disabled="saving" @click="resetForm">
            Reset
          </button>
          <button
            v-if="!createMode"
            class="btn-secondary border-red-300 text-red-700 hover:bg-red-50"
            type="button"
            :disabled="saving || deleting"
            @click="openDeleteModal"
          >
            {{ deleting ? 'Deleting...' : 'Delete' }}
          </button>
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
import { createTemplate, deleteTemplate, fetchTemplates, updateTemplate } from '@/modules/settings/api/templates';
import type { TemplateRecord } from '@/modules/settings/types';

type TemplateForm = {
  label: string;
  key: string;
  definition_json: string;
};

const templates = ref<TemplateRecord[]>([]);
const selectedId = ref<string | null>(null);
const saving = ref(false);
const deleting = ref(false);
const deleteModalOpen = ref(false);

const form = reactive<TemplateForm>({
  label: '',
  key: '',
  definition_json: '{}'
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
  form.definition_json = prettyJson(row.definition_json);
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
  form.definition_json = '{}';
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
      definition_json: normalizedDefinition.value
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

const prettyJson = (raw: string): string => {
  try {
    const parsed = JSON.parse(raw);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return raw || '{}';
  }
};

const normalizeDefinitionJson = (
  raw: string
): { ok: true; value: string } | { ok: false; message: string } => {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { ok: false, message: 'Definition JSON is required.' };
  }
  try {
    const parsed = JSON.parse(trimmed);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      return { ok: false, message: 'Definition JSON must be an object.' };
    }
    return { ok: true, value: JSON.stringify(parsed) };
  } catch {
    return { ok: false, message: 'Definition JSON must be valid JSON.' };
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
