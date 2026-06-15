import { createApp, h } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import PlaytestStackPopover from '@/modules/playtester/components/PlaytestStackPopover.vue';

vi.mock('@/api/client', () => ({
  toAbsoluteApiUrl: (url: string) => url,
}));

const mountPopover = (props: Partial<InstanceType<typeof PlaytestStackPopover>['$props']> = {}) => {
  const container = document.createElement('div');
  document.body.append(container);
  const app = createApp({
    render: () => h(PlaytestStackPopover, {
      open: true,
      title: 'Library',
      instances: [],
      cardBackUrl: null,
      ...props,
    }),
  });
  app.mount(container);

  return {
    container,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('PlaytestStackPopover', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('uses a measured bottom offset when provided', () => {
    const mounted = mountPopover({ bottomOffsetPx: 212 });

    const popover = mounted.container.querySelector<HTMLElement>('[data-testid="playtest-stack-overlay"]');
    expect(popover?.style.getPropertyValue('--playtester-stack-popover-bottom')).toBe('212px');

    mounted.unmount();
  });

  test('falls back to the shared setup placement before measurement', () => {
    const mounted = mountPopover();

    const popover = mounted.container.querySelector<HTMLElement>('[data-testid="playtest-stack-overlay"]');
    expect(popover?.style.getPropertyValue('--playtester-stack-popover-bottom')).toBe('');

    mounted.unmount();
  });
});
