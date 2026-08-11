import { describe, expect, test } from 'vitest';
import type { OperationsItemStatus, OperationsQueueItem } from '@/domain/operations/types';
import {
  extractImportJobErrorMessage,
  getContentVersionBaseError,
  getContentVersionBasePrefill,
  getImportSubmitLabel,
  getImportJobProgressPercent,
  getOperationsItemProgressPercent,
  getRecentImportJobs,
  hasActiveImportJobs,
} from '@/features/import-jobs/utils/importJobUtils';

const historyItem = (id: string, status: OperationsItemStatus): OperationsQueueItem => ({
  id,
  title: id,
  status,
  native_status: status,
  created_at: '2026-08-09T10:00:00Z',
  updated_at: '2026-08-09T10:01:00Z',
  started_at: null,
  finished_at: null,
  progress_current: 4,
  progress_total: 10,
  error_message: null,
  metadata: [],
  links: [],
});

describe('importJobs utils', () => {
  test('detects active jobs and computes progress safely', () => {
    expect(
      hasActiveImportJobs([
        {
          id: 'job-1',
          source_path: '/tmp/cards',
          template_id: 'template-1',
          content_version: null,
          status: 'running',
          total_items: 10,
          processed_items: 4,
          created_at: '',
          updated_at: '',
          card_pool: 'player',
          card_role_mode: 'automatic',
          card_role_override: [],
          template_role_snapshot: [],
          card_role_inference_policy_version: 1,
        },
      ]),
    ).toBe(true);

    expect(
      getImportJobProgressPercent({
        id: 'job-2',
        source_path: '/tmp/cards',
        template_id: 'template-1',
        content_version: null,
        status: 'completed',
        total_items: 0,
        processed_items: 0,
        created_at: '',
        updated_at: '',
        card_pool: 'player',
        card_role_mode: 'automatic',
        card_role_override: [],
        template_role_snapshot: [],
        card_role_inference_policy_version: 1,
      }),
    ).toBe(0);
  });

  test('normalizes structured error payloads', () => {
    expect(
      extractImportJobErrorMessage({
        response: {
          status: 400,
          data: {
            detail: [{ msg: 'Bad file' }],
          },
        },
      }),
    ).toBe('Bad file');
  });

  test('prefills the current base version and switches submit label', () => {
    const currentVersion = {
      id: 'version-1',
      version_number: '14.1.2',
      base_version: '14.1',
      description: 'Current release.',
    };

    expect(getContentVersionBasePrefill(currentVersion)).toBe('14.1');
    expect(getImportSubmitLabel('14.1', currentVersion)).toBe('Update Version');
    expect(getImportSubmitLabel('14.2', currentVersion)).toBe('Create Version');
  });

  test('validates content version base format strictly', () => {
    expect(getContentVersionBaseError('14.1')).toBe('');
    expect(getContentVersionBaseError(' 14.1 ')).toBe('');
    expect(getContentVersionBaseError('')).toBe('Enter a version.');
    expect(getContentVersionBaseError('asdflkjasdflkj')).toBe('Use major.minor format, for example 14.1.');
    expect(getContentVersionBaseError('1.0.0')).toBe('Use major.minor format, for example 14.1.');
    expect(getContentVersionBaseError('1.0.')).toBe('Use major.minor format, for example 14.1.');
  });

  test('selects at most five terminal history rows without active duplicates', () => {
    const items = [
      historyItem('active-job', 'completed'),
      historyItem('finished-1', 'completed'),
      historyItem('queued-job', 'queued'),
      historyItem('finished-2', 'failed'),
      historyItem('finished-3', 'cancelled'),
      historyItem('finished-4', 'completed'),
      historyItem('finished-5', 'completed'),
      historyItem('finished-6', 'completed'),
    ];

    expect(getRecentImportJobs(items, new Set(['active-job'])).map((item) => item.id)).toEqual([
      'finished-1',
      'finished-2',
      'finished-3',
      'finished-4',
      'finished-5',
    ]);
  });

  test('computes operations history progress when totals are available', () => {
    expect(getOperationsItemProgressPercent(historyItem('finished', 'completed'))).toBe(40);
    expect(
      getOperationsItemProgressPercent({
        ...historyItem('unknown', 'failed'),
        progress_total: null,
      }),
    ).toBeNull();
  });
});
