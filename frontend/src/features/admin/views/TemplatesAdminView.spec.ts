import { createApp, nextTick, ref } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import TemplatesAdminView from '@/features/admin/views/TemplatesAdminView.vue';

const { fetchTemplates, updateTemplate } = vi.hoisted(() => ({
  fetchTemplates: vi.fn(),
  updateTemplate: vi.fn(),
}));

vi.mock('@/domain/templates/api', () => ({
  createTemplate: vi.fn(),
  deleteTemplate: vi.fn(),
  fetchTemplates,
  queueTemplateReparse: vi.fn(),
  updateTemplate,
}));

vi.mock('@/features/admin/composables/useTemplatePreview', () => ({
  useTemplatePreview: () => ({
    previewCards: ref([]),
    previewLoading: ref(false),
    previewRegions: ref([]),
    previewScope: ref('template'),
    previewSearchQuery: ref(''),
    previewWarning: ref(''),
    restorePreviewCard: vi.fn(),
    selectedPreviewCard: ref(null),
    selectPreviewCard: vi.fn(),
    templateScopeAvailable: ref(false),
  }),
}));

vi.mock('vue-sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

const flushPromises = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
};

describe('TemplatesAdminView', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  test('edits only parsing configuration and does not expose classification hints', async () => {
    fetchTemplates.mockResolvedValue([
      {
        id: 'template-id',
        key: 'event-v1',
        label: 'Event',
        definition_json: '{"regions":[]}',
      },
    ]);
    updateTemplate.mockResolvedValue(undefined);

    const host = document.createElement('div');
    document.body.appendChild(host);
    const app = createApp(TemplatesAdminView);
    app.mount(host);
    await flushPromises();
    await nextTick();

    expect(host.textContent).not.toContain('Inferred card roles');
    expect(host.textContent).not.toContain('Inferred card factions');
    Array.from(host.querySelectorAll<HTMLButtonElement>('button'))
      .find((button) => button.textContent?.trim() === 'Save Changes')
      ?.click();
    await flushPromises();
    await nextTick();

    expect(updateTemplate).toHaveBeenCalledWith('template-id', {
      label: 'Event',
      definition_json: { regions: [] },
    });

    app.unmount();
  });
});
