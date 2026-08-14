/* eslint-disable vue/one-component-per-file */
import { createApp, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import ClassificationDefinitionDetail from './ClassificationDefinitionDetail.vue';

vi.mock('@/features/admin/api/catalog', () => ({
  createClassificationRule: vi.fn(),
  deleteClassificationRule: vi.fn(),
  updateClassificationRule: vi.fn(),
}));

vi.mock('vue-sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

describe('ClassificationDefinitionDetail', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  test('shows global per-pool rule state for a code-owned definition', async () => {
    const host = document.createElement('div');
    document.body.appendChild(host);
    const app = createApp(ClassificationDefinitionDetail, {
      definition: {
        id: 'role:location',
        key: 'location',
        label: 'Location',
        rank: 3,
        target_kind: 'role',
        derived: false,
        linked_card_counts: { player: 0, evil: 4, neutral: 0 },
        rule_counts: {
          player: { tag: 0, type: 0 },
          evil: { tag: 1, type: 0 },
          neutral: { tag: 0, type: 0 },
        },
        rules: [
          {
            id: 'rule-location',
            card_pool: 'evil',
            target_kind: 'role',
            target_key: 'location',
            source_kind: 'tag',
            source_id: 'tag-location',
            source_key: 'location',
            source_label: 'Location',
            enabled: true,
            created_at: '2026-08-14T10:00:00Z',
            updated_at: '2026-08-14T10:00:00Z',
          },
        ],
      },
      tags: [
        {
          id: 'tag-location',
          key: 'location',
          label: 'Location',
          identifiers: [],
          identifiers_text: '',
        },
      ],
      types: [],
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain('Location');
    expect(host.textContent).toContain('Player');
    expect(host.textContent).toContain('Evil');
    expect(host.textContent).toContain('Neutral');
    expect(host.textContent).toContain('4 linked cards');
    expect(host.textContent).toContain('Add inference rule');

    app.unmount();
  });

  test('keeps Normal read-only as a derived empty state', async () => {
    const host = document.createElement('div');
    document.body.appendChild(host);
    const app = createApp(ClassificationDefinitionDetail, {
      definition: {
        id: 'role:standard',
        key: 'standard',
        label: 'Normal',
        rank: 0,
        target_kind: 'role',
        derived: true,
        linked_card_counts: {},
        rule_counts: {},
        rules: [],
      },
      tags: [],
      types: [],
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain('derived empty state');
    expect(host.textContent).not.toContain('Add inference rule');

    app.unmount();
  });
});
