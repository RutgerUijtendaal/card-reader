import { createApp, nextTick } from 'vue';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import DeveloperDataSettingsSection from './DeveloperDataSettingsSection.vue';

const {
  createBuildMock,
  createGrantMock,
  downloadUrlMock,
  fetchBuildsMock,
  fetchCurrentMock,
  lockUrlMock,
} = vi.hoisted(() => ({
  createBuildMock: vi.fn(),
  createGrantMock: vi.fn(),
  downloadUrlMock: vi.fn((path: string) => `https://cards.example.test/api${path}`),
  fetchBuildsMock: vi.fn(),
  fetchCurrentMock: vi.fn(),
  lockUrlMock: vi.fn((path: string) => `https://cards.example.test/api${path}`),
}));

vi.mock('@/domain/developer-data/api', () => ({
  createDeveloperDataBuild: createBuildMock,
  createDeveloperDataGrant: createGrantMock,
  developerDataDownloadUrl: downloadUrlMock,
  developerDataLockUrl: lockUrlMock,
  fetchDeveloperDataBuilds: fetchBuildsMock,
  fetchCurrentDeveloperData: fetchCurrentMock,
}));

const flushPromises = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
  await nextTick();
};

const mountSection = async (canManage = false) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp(DeveloperDataSettingsSection, { canManage });
  app.mount(container);
  await flushPromises();
  return {
    container,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('DeveloperDataSettingsSection', () => {
  beforeEach(() => {
    fetchCurrentMock.mockReset();
    createGrantMock.mockReset();
    createBuildMock.mockReset();
    fetchBuildsMock.mockReset();
    downloadUrlMock.mockClear();
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('shows the unavailable state without presenting download actions', async () => {
    fetchCurrentMock.mockResolvedValue({ available: false });
    const mounted = await mountSection();

    expect(mounted.container.textContent).toContain('No developer bundle is currently available');
    expect(mounted.container.querySelector('a')).toBeNull();
    mounted.unmount();
  });

  test('uses direct navigation and generates, copies, and expires a bootstrap code', async () => {
    fetchCurrentMock.mockResolvedValue({
      available: true,
      bundle_version: 'dev-v1',
      format_version: 1,
      sha256: 'a'.repeat(64),
      size_bytes: 2_621_440,
      created_at: '2026-08-04T10:00:00Z',
      download_url: '/developer-data/bundles/dev-v1/download',
    });
    createGrantMock.mockResolvedValue({
      code: 'ABCDE-FGHJK-MNPQR-STUVW',
      expires_at: '2026-08-04T10:10:00Z',
    });
    const mounted = await mountSection();

    const download = mounted.container.querySelector<HTMLAnchorElement>('a');
    expect(download?.href).toBe(
      'https://cards.example.test/api/developer-data/bundles/dev-v1/download',
    );
    expect(download?.hasAttribute('download')).toBe(false);
    expect(mounted.container.textContent).toContain('2.5 MB');

    const generate = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Generate code'),
    );
    generate?.click();
    await flushPromises();
    expect(createGrantMock).toHaveBeenCalledOnce();
    expect(mounted.container.textContent).toContain('ABCDE-FGHJK-MNPQR-STUVW');
    expect(mounted.container.textContent).toContain('Expires');

    const copy = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Copy code'),
    );
    copy?.click();
    await flushPromises();
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('ABCDE-FGHJK-MNPQR-STUVW');
    expect(mounted.container.textContent).toContain('Copied');
    mounted.unmount();
  });

  test('lets staff queue builds and download a completed lock file', async () => {
    fetchCurrentMock.mockResolvedValue({ available: false });
    fetchBuildsMock.mockResolvedValue([
      {
        id: 'completed-build',
        bundle_version: 'dev-completed',
        status: 'succeeded',
        requested_by: 'staff-user',
        created_at: '2026-08-04T10:00:00Z',
        started_at: '2026-08-04T10:00:01Z',
        finished_at: '2026-08-04T10:01:00Z',
        format_version: 1,
        sha256: 'b'.repeat(64),
        size_bytes: 2000,
        error_message: null,
        lock_download_url: '/developer-data/builds/completed-build/lock',
      },
    ]);
    createBuildMock.mockResolvedValue({
      id: 'queued-build',
      bundle_version: 'dev-queued',
      status: 'queued',
      requested_by: 'staff-user',
      created_at: '2026-08-04T11:00:00Z',
      started_at: null,
      finished_at: null,
      format_version: null,
      sha256: null,
      size_bytes: null,
      error_message: null,
      lock_download_url: null,
    });
    const mounted = await mountSection(true);

    const lockDownload = Array.from(mounted.container.querySelectorAll<HTMLAnchorElement>('a')).find((link) =>
      link.textContent?.includes('Download lock file'),
    );
    expect(lockDownload?.href).toBe(
      'https://cards.example.test/api/developer-data/builds/completed-build/lock',
    );

    const buildButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Build new version'),
    );
    buildButton?.click();
    await flushPromises();

    expect(createBuildMock).toHaveBeenCalledOnce();
    expect(mounted.container.textContent).toContain('dev-queued');
    expect(mounted.container.textContent).toContain('Build in progress');
    mounted.unmount();
  });
});
