import { createApp, defineComponent, h, nextTick, ref } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardVersionParseFlagModal from '@/modules/card-detail/components/CardVersionParseFlagModal.vue';
import type { CardVersionDetail, ParseFlagCreatePayload } from '@/modules/card-detail/types';

const buildVersion = (): CardVersionDetail => ({
  id: 'card-1',
  key: 'card-1',
  label: 'Card 1',
  is_hero: false,
  deck_building_config: { overrides: {} },
  template_id: 'template-1',
  version_id: 'version-1',
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  content_version: null,
  editable: false,
  name: 'Parsed Name',
  image_url: '/card.png',
  mana_cost: '2',
  mana_symbols: [],
  mana_value: 2,
  attack: null,
  health: null,
  type_line: 'Creature',
  rules_text: 'Parsed rules',
  rules_text_enriched: 'Parsed rules',
  confidence: 0.6,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  keywords: ['Arrival'],
  tags: [{ id: 'tag-1', key: 'animal', label: 'Animal' }],
  symbols: [],
  types: [{ id: 'type-1', key: 'creature', label: 'Creature' }],
  keyword_ids: [],
  tag_ids: ['tag-1'],
  symbol_ids: [],
  type_ids: ['type-1'],
  field_sources: {
    fields: {
      name: 'auto',
      type_line: 'auto',
      mana_cost: 'auto',
      attack: 'auto',
      health: 'auto',
      rules_text: 'auto',
    },
    metadata: {
      keywords: 'auto',
      tags: 'auto',
      types: 'auto',
      symbols: 'auto',
    },
  },
  parsed_snapshot: {
    fields: {
      name: 'Parsed Name',
      type_line: 'Creature',
      mana_cost: '2',
      attack: null,
      health: null,
      rules_text: 'Parsed rules',
    },
    metadata: {
      keyword_ids: [],
      tag_ids: ['tag-1'],
      type_ids: ['type-1'],
      symbol_ids: [],
    },
  },
  parse_result: null,
});

const mountModal = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const submit = vi.fn<(payload: ParseFlagCreatePayload) => void>();
  const open = ref(true);
  const app = createApp(
    defineComponent({
      setup() {
        return () =>
          h(CardVersionParseFlagModal, {
            open: open.value,
            version: buildVersion(),
            submitting: false,
            errorMessage: '',
            onClose: () => {
              open.value = false;
            },
            onSubmit: submit,
          });
      },
    }),
  );
  app.mount(container);
  await nextTick();
  return {
    container,
    submit,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

const clickButton = async (container: HTMLElement, label: string): Promise<void> => {
  const button = Array.from(container.querySelectorAll('button')).find(
    (candidate) => candidate.textContent?.replace(/\s+/g, ' ').trim().includes(label),
  );
  expect(button).toBeInstanceOf(HTMLButtonElement);
  (button as HTMLButtonElement).click();
  await nextTick();
};

describe('CardVersionParseFlagModal', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('submits multiple selected properties as separate items', async () => {
    const mounted = await mountModal();

    await clickButton(mounted.container, 'Name');

    const inputs = Array.from(mounted.container.querySelectorAll('input.input-base'));
    expect(inputs).toHaveLength(1);
    (inputs[0] as HTMLInputElement).value = 'Correct Name';
    inputs[0].dispatchEvent(new Event('input'));
    await nextTick();

    await clickButton(mounted.container, 'Rules Text');

    await clickButton(mounted.container, 'Submit Flag');

    expect(mounted.submit).toHaveBeenCalledWith({
      note: '',
      items: [
        { property_key: 'name', expected_value: 'Correct Name', note: '' },
        { property_key: 'rules_text', expected_value: '', note: '' },
      ],
    });
    mounted.unmount();
  });
});
