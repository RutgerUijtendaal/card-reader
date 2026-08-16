import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import type { OperationsQueueItem } from '@/domain/operations/types';
import ImportActivityPanel from '@/features/import-jobs/components/ImportActivityPanel.vue';
import type { ImportJob, ImportJobDetail } from '@/features/import-jobs/types';

const activeJob: ImportJob = {
  id: 'active-job',
  source_path: 'uploads/active-job',
  template_id: 'mtg-like-v1',
  content_version: null,
  status: 'running',
  total_items: 10,
  processed_items: 4,
  created_at: '2026-08-09T10:00:00Z',
  updated_at: '2026-08-09T10:01:00Z',
  card_pool: 'player',
  card_role_mode: 'automatic',
  card_role_override: [],
  card_faction_mode: 'automatic',
  card_faction_override: [],
  card_mana_family_mode: 'automatic',
  card_mana_family_override: [],
  classification_rule_snapshot: {
    schema_version: 1,
    card_pool: 'player',
    rules: [],
    digest: 'abc123',
  },
};

const recentJob: OperationsQueueItem = {
  id: 'finished-job',
  title: 'Default card · 16.2.0',
  status: 'completed',
  native_status: 'completed',
  created_at: '2026-08-09T09:00:00Z',
  updated_at: '2026-08-09T09:05:00Z',
  started_at: null,
  finished_at: null,
  progress_current: 10,
  progress_total: 10,
  error_message: null,
  metadata: [{ label: 'Source', value: 'uploads/finished-job' }],
  links: [],
};

const mountPanel = async (
  options: {
    activeJobs?: ImportJob[];
    recentJobs?: OperationsQueueItem[];
    activeLoaded?: boolean;
    historyLoaded?: boolean;
    selectedJobDetail?: ImportJobDetail | null;
  } = {},
) => {
  const onRefresh = vi.fn();
  const onCancel = vi.fn();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/operations', component: { template: '<div />' } },
      { path: '/cards/:cardId/edit', component: { template: '<div />' } },
    ],
  });
  await router.push('/operations');
  await router.isReady();
  const host = document.createElement('div');
  document.body.appendChild(host);
  const app = createApp(ImportActivityPanel, {
    activeJobs: options.activeJobs ?? [activeJob],
    recentJobs: options.recentJobs ?? [recentJob],
    activeLoaded: options.activeLoaded ?? true,
    historyLoaded: options.historyLoaded ?? true,
    refreshing: false,
    errorMessage: '',
    queuedCount: 0,
    runningCount: 1,
    cancelingCount: 0,
    cancellingJobIds: new Set<string>(),
    lastRefreshedAt: '10:05:00',
    selectedJobDetail: options.selectedJobDetail ?? null,
    detailLoading: false,
    onRefresh,
    onCancel,
  });
  app.use(router);
  app.mount(host);
  return { app, host, onRefresh, onCancel };
};

describe('ImportActivityPanel', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('shows cancellable active work and compact recent history inline', async () => {
    const mounted = await mountPanel();

    expect(mounted.host.querySelector('aside')).toBeNull();
    expect(
      mounted.host
        .querySelector('[data-testid="import-activity-panel"]')
        ?.classList.contains('theme-card-frame'),
    ).toBe(false);
    expect(mounted.host.textContent).toContain('mtg-like-v1 · Unversioned');
    expect(mounted.host.textContent).toContain('Default card · 16.2.0');
    expect(mounted.host.textContent).not.toContain('uploads/finished-job');
    expect(
      mounted.host.querySelector('a[href="/operations#queue-imports"]')?.textContent,
    ).toContain('Full history');
    const actions = mounted.host.querySelector('[data-testid="import-activity-actions"]');
    expect(actions?.classList.contains('flex-nowrap')).toBe(true);
    expect(actions?.classList.contains('flex-wrap')).toBe(false);

    mounted.host.querySelector<HTMLButtonElement>('button[aria-label="Refresh import activity"]')?.click();
    Array.from(mounted.host.querySelectorAll('button'))
      .find((button) => button.textContent?.trim() === 'Interrupt')
      ?.click();
    await nextTick();

    expect(mounted.onRefresh).toHaveBeenCalledOnce();
    expect(mounted.onCancel).toHaveBeenCalledWith('active-job');

    mounted.app.unmount();
  });

  test('uses concise empty states without hiding history access', async () => {
    const mounted = await mountPanel({ activeJobs: [], recentJobs: [] });

    expect(mounted.host.textContent).toContain('No active imports.');
    expect(mounted.host.textContent).toContain('No recent import history.');
    expect(mounted.host.querySelector('a[href="/operations#queue-imports"]')).not.toBeNull();

    mounted.app.unmount();
  });

  test('shows active controls while recent history is still loading', async () => {
    const mounted = await mountPanel({ historyLoaded: false });

    expect(mounted.host.textContent).toContain('mtg-like-v1 · Unversioned');
    expect(mounted.host.textContent).toContain('Interrupt');
    expect(mounted.host.querySelector('[aria-label="Loading active imports"]')).toBeNull();
    expect(
      mounted.host.querySelector('[aria-label="Loading recent import history"]'),
    ).not.toBeNull();

    mounted.app.unmount();
  });

  test('shows every item warning and links classification mismatches to the Card tab', async () => {
    const detail: ImportJobDetail = {
      ...activeJob,
      id: 'finished-job',
      status: 'completed',
      processed_items: 1,
      total_items: 1,
      items: [
        {
          id: 'item-id',
          source_file: 'event.webp',
          status: 'completed',
          error_message: null,
          warning_code: 'matched_deprecated_card',
          warning_message: 'Matched a deprecated card.',
          warnings: [
            { code: 'matched_deprecated_card', message: 'Matched a deprecated card.' },
            {
              code: 'card_classification_mismatch',
              message: 'Inferred roles differ from the existing card.',
              details: {
                inferred: { card_pool: 'evil', card_roles: ['event'] },
                existing: { card_pool: 'player', card_roles: [] },
              },
            },
            {
              code: 'card_classification_changed_while_queued',
              message: 'Classification changed while queued.',
              details: {
                queued: { card_pool: 'player', card_roles: ['hero'] },
                live: { card_pool: 'player', card_roles: [] },
              },
            },
            {
              code: 'evil_faction_unresolved',
              message: 'No Evil faction was inferred.',
              details: {
                reason: 'ambiguous_name',
                checksum_candidate_count: 0,
                name_candidate_count: 2,
              },
            },
          ],
          resolved_card_roles: ['event'],
          resolved_card_factions: ['order'],
          resolved_card_mana_families: ['arcane'],
          classification_inference: {
            roles: {
              mode: 'automatic',
              matched_type_sources: [{ id: 'type-event', key: 'event' }],
            },
            factions: {
              mode: 'automatic',
              matched_tag_sources: [{ id: 'tag-order', key: 'order' }],
            },
          },
          target_card_id: 'card-id',
          target_card_version_id: 'version-id',
          target_card_pool_snapshot: null,
          target_card_roles_snapshot: [],
          target_card_factions_snapshot: [],
          target_card_mana_families_snapshot: [],
          card_tab_url: '/cards/card-id/edit?tab=card',
        },
      ],
    };
    const mounted = await mountPanel({ selectedJobDetail: detail });

    expect(mounted.host.textContent).toContain('Matched a deprecated card.');
    expect(mounted.host.textContent).toContain('Inferred roles differ from the existing card.');
    expect(mounted.host.textContent).toContain('Classification changed while queued.');
    expect(mounted.host.textContent).toContain('No Evil faction was inferred.');
    expect(mounted.host.textContent).toContain('Ambiguous name or alias');
    expect(mounted.host.textContent).toContain('Name candidates:');
    expect(mounted.host.textContent).toContain('Role types');
    expect(mounted.host.textContent).toContain('Inferred');
    expect(mounted.host.textContent).toContain('Evil');
    expect(mounted.host.textContent).toContain('Existing');
    expect(mounted.host.textContent).toContain('Queued');
    expect(mounted.host.textContent).toContain('Live');
    expect(mounted.host.textContent).toContain('Normal');
    expect(mounted.host.textContent).toContain('Factions: Order');
    expect(
      mounted.host.querySelector('a[href="/cards/card-id/edit?tab=card"]')?.textContent,
    ).toContain('Review card classification');
    expect(
      mounted.host.querySelectorAll('a[href="/cards/card-id/edit?tab=card"]'),
    ).toHaveLength(2);

    mounted.app.unmount();
  });

  test('does not present unprocessed classification defaults as resolved Normal cards', async () => {
    const detail: ImportJobDetail = {
      ...activeJob,
      items: [
        {
          id: 'queued-item',
          source_file: 'queued.webp',
          status: 'queued',
          error_message: null,
          warning_code: null,
          warning_message: null,
          warnings: [],
          resolved_card_roles: [],
          resolved_card_factions: [],
          resolved_card_mana_families: [],
          classification_inference: {},
          target_card_id: null,
          target_card_version_id: null,
          target_card_pool_snapshot: null,
          target_card_roles_snapshot: [],
          target_card_factions_snapshot: [],
          target_card_mana_families_snapshot: [],
          card_tab_url: null,
        },
        {
          id: 'failed-item',
          source_file: 'failed.webp',
          status: 'failed',
          error_message: 'OCR failed.',
          warning_code: null,
          warning_message: null,
          warnings: [],
          resolved_card_roles: [],
          resolved_card_factions: [],
          resolved_card_mana_families: [],
          classification_inference: {},
          target_card_id: null,
          target_card_version_id: null,
          target_card_pool_snapshot: null,
          target_card_roles_snapshot: [],
          target_card_factions_snapshot: [],
          target_card_mana_families_snapshot: [],
          card_tab_url: null,
        },
      ],
    };
    const mounted = await mountPanel({ selectedJobDetail: detail });

    expect(mounted.host.textContent).toContain('Classification pending');
    expect(mounted.host.textContent).toContain('Classification unavailable');
    expect(mounted.host.textContent).not.toContain('Normal — no special roles');
    expect(mounted.host.textContent).not.toContain('Resolution');

    mounted.app.unmount();
  });
});
