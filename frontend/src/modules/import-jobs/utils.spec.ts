import { describe, expect, test } from 'vitest';
import {
  extractImportJobErrorMessage,
  getImportJobProgressPercent,
  hasActiveImportJobs,
} from '@/modules/import-jobs/utils';

describe('importJobs utils', () => {
  test('detects active jobs and computes progress safely', () => {
    expect(
      hasActiveImportJobs([
        {
          id: 'job-1',
          source_path: '/tmp/cards',
          template_id: 'template-1',
          status: 'running',
          total_items: 10,
          processed_items: 4,
          created_at: '',
          updated_at: '',
        },
      ]),
    ).toBe(true);

    expect(
      getImportJobProgressPercent({
        id: 'job-2',
        source_path: '/tmp/cards',
        template_id: 'template-1',
        status: 'completed',
        total_items: 0,
        processed_items: 0,
        created_at: '',
        updated_at: '',
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
});
