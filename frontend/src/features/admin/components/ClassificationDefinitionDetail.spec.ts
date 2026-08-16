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
      symbols: [],
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
      symbols: [],
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain('derived empty state');
    expect(host.textContent).not.toContain('Add inference rule');

    app.unmount();
  });

  test('shows mana-family symbol rules in the shared classification editor', async () => {
    const host = document.createElement('div');
    document.body.appendChild(host);
    const app = createApp(ClassificationDefinitionDetail, {
      definition: {
        id: 'mana_family:arcane',
        key: 'arcane',
        label: 'Arcane',
        rank: 0,
        target_kind: 'mana_family',
        derived: false,
        linked_card_counts: { player: 12 },
        rule_counts: { player: { tag: 0, type: 0, symbol: 1 } },
        rules: [
          {
            id: 'rule-arcane-mana',
            card_pool: 'player',
            target_kind: 'mana_family',
            target_key: 'arcane',
            source_kind: 'symbol',
            source_id: 'symbol-arcane-mana',
            source_key: 'arcane-mana',
            source_label: 'Arcane Mana',
            enabled: true,
            created_at: '2026-08-16T10:00:00Z',
            updated_at: '2026-08-16T10:00:00Z',
          },
        ],
        display_symbol_key: 'arcane-mana',
        display_symbol: {
          id: 'symbol-arcane-mana',
          key: 'arcane-mana',
          label: 'Arcane Mana',
        },
      },
      tags: [],
      types: [],
      symbols: [
        {
          id: 'symbol-arcane-mana',
          key: 'arcane-mana',
          label: 'Arcane Mana',
          symbol_type: 'mana',
          detector_type: 'template',
          detection_config_json: '{}',
          text_enrichment_json: '{}',
          reference_assets_json: '[]',
          text_token: '{AM}',
          enabled: true,
        },
      ],
    });
    app.mount(host);
    await nextTick();

    expect(host.textContent).toContain('Mana Family');
    expect(host.textContent).toContain('12 linked cards · 1 rules');
    expect(host.textContent).toContain('symbol');

    app.unmount();
  });
});
