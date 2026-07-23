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
  await nextTick();
  return {
    container,
    modalRoot: document.body,
    open,
    submit,
    setOpen: async (value: boolean) => {
      open.value = value;
      await nextTick();
    },
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

const findButton = (container: HTMLElement, label: string): HTMLButtonElement => {
  const button = Array.from(container.querySelectorAll('button')).find((candidate) =>
    candidate.textContent?.replace(/\s+/g, ' ').trim().includes(label),
  );
  expect(button).toBeInstanceOf(HTMLButtonElement);
  return button as HTMLButtonElement;
};

const clickButton = async (container: HTMLElement, label: string): Promise<void> => {
  findButton(container, label).click();
  await nextTick();
};

const setInputValue = async (
  input: HTMLInputElement | HTMLTextAreaElement,
  value: string,
): Promise<void> => {
  input.value = value;
  input.dispatchEvent(new Event('input'));
  await nextTick();
};

describe('CardVersionParseFlagModal', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('opens the overall suggestion tab by default without flagging it', async () => {
    const mounted = await mountModal();
    const overallButton = findButton(mounted.modalRoot, 'Overall card suggestion');
    const overallIndicator = overallButton.querySelector('[data-tab-selected-indicator]');

    expect(overallButton.getAttribute('aria-pressed')).toBe('true');
    expect(overallButton.classList).not.toContain('theme-selected-surface');
    expect(overallIndicator?.classList).toContain('bg-[var(--color-control-accent)]');
    expect(mounted.modalRoot.querySelector('textarea[placeholder="Required"]')).toBeInstanceOf(
      HTMLTextAreaElement,
    );
    expect(document.activeElement).toBe(
      mounted.modalRoot.querySelector('textarea[placeholder="Required"]'),
    );
    expect(findButton(mounted.modalRoot, 'Submit Flag').disabled).toBe(true);
    mounted.unmount();
  });

  test('submits multiple selected properties as separate items', async () => {
    const mounted = await mountModal();

    await clickButton(mounted.modalRoot, 'Name');

    const inputs = Array.from(mounted.modalRoot.querySelectorAll('input.input-base'));
    expect(inputs).toHaveLength(1);
    await setInputValue(inputs[0] as HTMLInputElement, 'Correct Name');

    await clickButton(mounted.modalRoot, 'Rules Text');
    await setInputValue(
      mounted.modalRoot.querySelector('input.input-base') as HTMLInputElement,
      'Correct rules',
    );

    await clickButton(mounted.modalRoot, 'Submit Flag');

    expect(mounted.submit).toHaveBeenCalledWith({
      note: '',
      items: [
        { property_key: 'name', expected_value: 'Correct Name', note: '' },
        { property_key: 'rules_text', expected_value: 'Correct rules', note: '' },
      ],
    });
    mounted.unmount();
  });

  test('uses expected values to activate property flags while row clicks only switch tabs', async () => {
    const mounted = await mountModal();

    await clickButton(mounted.modalRoot, 'Name');
    await nextTick();
    expect(
      findButton(mounted.modalRoot, 'Overall card suggestion').querySelector(
        '[data-tab-selected-indicator]',
      ),
    ).toBeNull();
    expect(
      findButton(mounted.modalRoot, 'Name')
        .querySelector('[data-tab-selected-indicator]')
        ?.classList,
    ).toContain('bg-[var(--color-control-accent)]');
    expect(document.activeElement).toBe(mounted.modalRoot.querySelector('input.input-base'));
    expect(findButton(mounted.modalRoot, 'Name').classList).not.toContain('theme-selected-surface');
    expect(findButton(mounted.modalRoot, 'Submit Flag').disabled).toBe(true);

    await setInputValue(
      mounted.modalRoot.querySelector('input.input-base') as HTMLInputElement,
      'Correct Name',
    );
    expect(findButton(mounted.modalRoot, 'Name').classList).toContain('theme-selected-surface');
    expect(findButton(mounted.modalRoot, 'Name').textContent).toContain('Active');
    expect(findButton(mounted.modalRoot, 'Submit Flag').disabled).toBe(false);

    await clickButton(mounted.modalRoot, 'Rules Text');
    expect(findButton(mounted.modalRoot, 'Name').classList).toContain('theme-selected-surface');
    expect(findButton(mounted.modalRoot, 'Rules Text').classList).not.toContain('theme-selected-surface');

    await clickButton(mounted.modalRoot, 'Name');
    expect((mounted.modalRoot.querySelector('input.input-base') as HTMLInputElement).value).toBe(
      'Correct Name',
    );
    await setInputValue(mounted.modalRoot.querySelector('input.input-base') as HTMLInputElement, '');
    expect(findButton(mounted.modalRoot, 'Name').classList).not.toContain('theme-selected-surface');
    expect(findButton(mounted.modalRoot, 'Submit Flag').disabled).toBe(true);

    expect(mounted.modalRoot.querySelectorAll('input[type="checkbox"]')).toHaveLength(0);
    mounted.unmount();
  });

  test('requires text for an overall suggestion and submits it with property issues', async () => {
    const mounted = await mountModal();

    await clickButton(mounted.modalRoot, 'Overall card suggestion');
    expect(findButton(mounted.modalRoot, 'Submit Flag').disabled).toBe(true);

    const suggestion = mounted.modalRoot.querySelector('textarea[placeholder="Required"]');
    expect(suggestion).toBeInstanceOf(HTMLTextAreaElement);
    await setInputValue(suggestion as HTMLTextAreaElement, 'Give this card a clearer role.');
    expect(findButton(mounted.modalRoot, 'Overall card suggestion').classList).toContain(
      'theme-selected-surface',
    );
    expect(findButton(mounted.modalRoot, 'Submit Flag').disabled).toBe(false);

    await clickButton(mounted.modalRoot, 'Name');
    await setInputValue(
      mounted.modalRoot.querySelector('input.input-base') as HTMLInputElement,
      'Clearer Card Name',
    );
    await clickButton(mounted.modalRoot, 'Submit Flag');

    expect(mounted.submit).toHaveBeenCalledWith({
      note: '',
      items: [
        {
          property_key: 'overall',
          expected_value: '',
          note: 'Give this card a clearer role.',
        },
        { property_key: 'name', expected_value: 'Clearer Card Name', note: '' },
      ],
    });
    mounted.unmount();
  });

  test('resets drafted flag items after closing', async () => {
    const mounted = await mountModal();

    await clickButton(mounted.modalRoot, 'Name');
    await setInputValue(
      mounted.modalRoot.querySelector('input.input-base') as HTMLInputElement,
      'Correct Name',
    );

    await mounted.setOpen(false);
    await mounted.setOpen(true);

    expect(findButton(mounted.modalRoot, 'Name').classList).not.toContain('theme-selected-surface');
    expect(findButton(mounted.modalRoot, 'Submit Flag').disabled).toBe(true);
    expect(findButton(mounted.modalRoot, 'Overall card suggestion').getAttribute('aria-pressed')).toBe('true');
    mounted.unmount();
  });
});
