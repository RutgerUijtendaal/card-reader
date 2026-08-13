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

  test('edits inferred roles and factions separately from the parsing definition', async () => {
    fetchTemplates.mockResolvedValue([
      {
        id: 'template-id',
        key: 'event-v1',
        label: 'Event',
        definition_json: '{"regions":[]}',
        inferred_card_roles: ['event'],
        inferred_card_factions: ['order'],
      },
    ]);
    updateTemplate.mockResolvedValue(undefined);

    const host = document.createElement('div');
    document.body.appendChild(host);
    const app = createApp(TemplatesAdminView);
    app.mount(host);
    await flushPromises();
    await nextTick();

    const checkboxes = Array.from(host.querySelectorAll<HTMLInputElement>('input[type="checkbox"]'));
    expect(checkboxes).toHaveLength(9);

    const labels = Array.from(host.querySelectorAll('label'));
    const locationInput = labels.find((label) => label.textContent?.includes('Location'))
      ?.querySelector<HTMLInputElement>('input');
    const bloodInput = labels.find((label) => label.textContent?.includes('Blood'))
      ?.querySelector<HTMLInputElement>('input');
    expect(locationInput?.checked).toBe(false);
    expect(bloodInput?.checked).toBe(false);
    locationInput?.click();
    bloodInput?.click();
    Array.from(host.querySelectorAll<HTMLButtonElement>('button'))
      .find((button) => button.textContent?.trim() === 'Save Changes')
      ?.click();
    await flushPromises();
    await nextTick();

    expect(updateTemplate).toHaveBeenCalledWith('template-id', {
      label: 'Event',
      definition_json: { regions: [] },
      inferred_card_roles: ['event', 'location'],
      inferred_card_factions: ['order', 'blood'],
    });

    app.unmount();
  });
});
