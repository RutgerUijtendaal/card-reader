import { describe, expect, test } from 'vitest';
import {
  extractImportJobErrorMessage,
  getContentVersionBaseError,
  getContentVersionBasePrefill,
  getImportSubmitLabel,
  getImportJobProgressPercent,
  hasActiveImportJobs,
} from '@/modules/import-jobs/utils/importJobUtils';

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
});
