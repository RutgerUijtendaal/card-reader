import { createApp, defineComponent, h, nextTick, reactive, ref } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardVersionEditorPane from '@/modules/card-detail/components/CardVersionEditorPane.vue';
import type {
  CardVersionDetail,
  EditorForm,
  ReparseTemplateOption,
} from '@/modules/card-detail/types';

vi.mock('@/api/client', () => ({
  toAbsoluteApiUrl: (url: string) => url,
}));

const buildVersion = (overrides: Partial<CardVersionDetail> = {}): CardVersionDetail => ({
  id: 'card-1',
  key: 'card-1',
  label: 'Card 1',
  is_hero: false,
  template_id: 'template-1',
  version_id: 'version-1',
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  editable: true,
  name: 'Card 1',
  image_url: '/card.png',
  mana_cost: '1',
  mana_symbols: [],
  mana_value: 1,
  attack: null,
  health: null,
  type_line: 'Item',
  rules_text: '',
  rules_text_enriched: '',
  confidence: 1,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
  keyword_ids: [],
  tag_ids: [],
  symbol_ids: [],
  type_ids: [],
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
      name: 'Card 1',
      type_line: 'Item',
      mana_cost: '1',
      attack: null,
      health: null,
      rules_text: '',
    },
    metadata: {
      keyword_ids: [],
      tag_ids: [],
      type_ids: [],
      symbol_ids: [],
    },
  },
  parse_result: null,
  ...overrides,
});

const buildForm = (overrides: Partial<EditorForm> = {}): EditorForm => ({
  name: 'Card 1',
  type_line: 'Item',
  mana_cost: '1',
  attack: '',
  health: '',
  rules_text: '',
  is_hero: false,
  lifecycle_status: 'active',
  keyword_ids: [],
  tag_ids: [],
  type_ids: [],
  additional_symbol_ids: [],
  ...overrides,
});
const autoSource = (): 'auto' => 'auto';
const autoLabel = (): string => 'Auto';
const noSuggestion = (): boolean => false;
const emptyText = (): string => '';
const emptyIds = (): string[] => [];
const emptyOptions = (): [] => [];

const mountPane = async ({
  deprecatedStatusDisabled = false,
}: {
  deprecatedStatusDisabled?: boolean;
} = {}) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const updateLifecycleStatus = vi.fn();
  const form = reactive(buildForm());
  const reparseTemplateId = ref('template-1');
  const reparseTemplates: ReparseTemplateOption[] = [
    { id: 'template-1', key: 'template-1', label: 'Default' },
  ];
  const app = createApp(
    defineComponent({
      setup() {
        return () =>
          h(CardVersionEditorPane, {
            version: buildVersion(),
            form,
            reparseTemplates,
            reparseTemplateId: reparseTemplateId.value,
            isBusy: false,
            isSaving: false,
            isQueuingReparse: false,
            saveMessage: '',
            fieldSource: autoSource,
            metadataSource: autoSource,
            fieldSourceLabel: autoLabel,
            metadataSourceLabel: autoLabel,
            fieldHasParsedSuggestion: noSuggestion,
            formatParsedFieldValue: emptyText,
            metadataHasParsedSuggestion: noSuggestion,
            metadataSearch: {
              keywords: '',
              tags: '',
              types: '',
              symbols: '',
            },
            selectedIds: emptyIds,
            parsedMetadataLabels: emptyIds,
            optionsForGroup: emptyOptions,
            ruleTextSymbols: [],
            additionalSymbolIds: [],
            ruleTextUnknownSymbolKeys: [],
            deprecatedStatusDisabled,
            onUpdateLifecycleStatus: updateLifecycleStatus,
          });
      },
    }),
  );
  app.mount(container);
  await nextTick();

  return {
    container,
    updateLifecycleStatus,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('CardVersionEditorPane lifecycle status', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('disables deprecated status when the card is a group anchor', async () => {
    const mounted = await mountPane({ deprecatedStatusDisabled: true });
    const deprecatedButton = mounted.container.querySelector('[data-testid="lifecycle-option-deprecated"]');

    expect(deprecatedButton).toBeInstanceOf(HTMLButtonElement);
    expect((deprecatedButton as HTMLButtonElement).disabled).toBe(true);
    expect(mounted.container.textContent).toContain('Group anchors must stay active');

    (deprecatedButton as HTMLButtonElement).click();
    await nextTick();

    expect(mounted.updateLifecycleStatus).not.toHaveBeenCalled();
    mounted.unmount();
  });

  test('keeps deprecated status selectable for non-anchor cards', async () => {
    const mounted = await mountPane();
    const deprecatedButton = mounted.container.querySelector('[data-testid="lifecycle-option-deprecated"]');

    expect(deprecatedButton).toBeInstanceOf(HTMLButtonElement);
    expect((deprecatedButton as HTMLButtonElement).disabled).toBe(false);

    (deprecatedButton as HTMLButtonElement).click();
    await nextTick();

    expect(mounted.updateLifecycleStatus).toHaveBeenCalledWith('deprecated');
    mounted.unmount();
  });
});
