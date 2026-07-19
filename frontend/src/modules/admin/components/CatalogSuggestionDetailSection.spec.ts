/* eslint-disable vue/one-component-per-file */
import { createApp, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CatalogSuggestionDetailSection from '@/modules/admin/components/CatalogSuggestionDetailSection.vue';
import type { SuggestionRecord } from '@/modules/admin/types';

const rejectedSuggestion: SuggestionRecord = {
  id: 'suggestion-1',
  kind: 'type',
  display_value: 'Tempo Burst',
  normalized_value: 'tempo burst',
  status: 'rejected',
  occurrence_count: 2,
  active_occurrence_count: 1,
  rejected_resubmission_count: 3,
  accepted_target: null,
  occurrences: [],
  linked_decks: [],
  label: 'Tempo Burst',
  key: 'tempo burst',
};

afterEach(() => {
  document.body.innerHTML = '';
});

describe('CatalogSuggestionDetailSection', () => {
  test('shows rejected demand and emits the deck suggestion reopen action', async () => {
    const onReopen = vi.fn();
    const container = document.createElement('div');
    document.body.appendChild(container);
    const app = createApp(CatalogSuggestionDetailSection, {
      selectedKind: 'suggested-deck-types',
      selectedRow: rejectedSuggestion,
      existingOptions: [],
      existingTargetId: '',
      newLabel: 'Tempo Burst',
      newKey: '',
      actionLoading: false,
      kindItemLabel: () => 'Type Tag Suggestion',
      onReopen,
    });
    app.mount(container);
    await nextTick();

    expect(container.textContent).toContain('3 resubmissions after rejection');
    expect(container.textContent).toContain('1 active deck, 2 total occurrences');
    expect(container.textContent).not.toContain('Accept as existing');
    expect(container.textContent).not.toContain('Accept as new');
    expect(container.textContent).not.toContain('Reject');
    const reopenButton = [...container.querySelectorAll('button')]
      .find((button) => button.textContent?.trim() === 'Reopen Suggestion');
    expect(reopenButton).toBeDefined();
    reopenButton?.click();
    expect(onReopen).toHaveBeenCalledTimes(1);

    app.unmount();
  });

  test('does not expose transition actions for accepted suggestions', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const app = createApp(CatalogSuggestionDetailSection, {
      selectedKind: 'suggested-deck-types',
      selectedRow: {
        ...rejectedSuggestion,
        status: 'accepted',
        rejected_resubmission_count: 0,
        accepted_target: { id: 'type-1', key: 'tempo-burst', label: 'Tempo Burst' },
      },
      existingOptions: [],
      existingTargetId: '',
      newLabel: 'Tempo Burst',
      newKey: '',
      actionLoading: false,
      kindItemLabel: () => 'Type Tag Suggestion',
    });
    app.mount(container);
    await nextTick();

    expect(container.textContent).not.toContain('Accept as existing');
    expect(container.textContent).not.toContain('Accept as new');
    expect(container.textContent).not.toContain('Reject');
    expect(container.textContent).not.toContain('Reopen Suggestion');

    app.unmount();
  });
});
