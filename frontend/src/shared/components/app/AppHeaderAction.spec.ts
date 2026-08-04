/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick, type Component } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';

const TestIcon = defineComponent({
  setup() {
    return () => h('svg', { 'data-testid': 'action-icon' });
  },
});

const mountAction = async (
  props: {
    icon?: Component;
    label: string;
    shortLabel: string;
    to?: string;
    variant?: 'primary' | 'secondary' | 'tab';
    disabled?: boolean;
    active?: boolean;
    iconClass?: string;
    onClick?: (event: MouseEvent) => void;
  },
  trailing?: () => ReturnType<typeof h>,
) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/target', component: { template: '<div />' } },
    ],
  });
  await router.push('/');
  await router.isReady();

  const Root = defineComponent({
    setup() {
      return () => h(
        AppHeaderAction,
        { icon: TestIcon, ...props },
        trailing ? { trailing } : undefined,
      );
    },
  });
  const app = createApp(Root);
  app.use(router);
  app.mount(container);
  await nextTick();

  return {
    container,
    router,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('AppHeaderAction', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('renders a naturally sized primary link with a 16px icon and full accessible label', async () => {
    const mounted = await mountAction({
      label: 'Build a deck',
      shortLabel: 'Build a deck',
      to: '/target',
      variant: 'primary',
    });
    const link = mounted.container.querySelector<HTMLAnchorElement>('a');
    const icon = link?.querySelector<SVGElement>('[data-testid="action-icon"]');

    expect(link?.getAttribute('href')).toBe('/target');
    expect(link?.getAttribute('aria-label')).toBe('Build a deck');
    expect(link?.textContent).toBe('Build a deck');
    expect(link?.classList.contains('h-10')).toBe(true);
    expect(link?.classList.contains('w-auto')).toBe(true);
    expect(link?.classList.contains('btn-primary')).toBe(true);
    expect(icon?.classList.contains('h-4')).toBe(true);
    expect(icon?.classList.contains('w-4')).toBe(true);

    mounted.unmount();
  });

  test('shows the full tooltip on hover and focus', async () => {
    const mounted = await mountAction({
      label: 'Copy Mainboard TTS',
      shortLabel: 'TTS',
    });
    const trigger = mounted.container.querySelector<HTMLElement>('.inline-flex');
    const button = mounted.container.querySelector<HTMLButtonElement>('button');

    trigger?.dispatchEvent(new MouseEvent('mouseenter'));
    await nextTick();
    expect(document.body.querySelector('[role="tooltip"]')?.textContent).toBe('Copy Mainboard TTS');
    expect(button?.getAttribute('aria-describedby')).toBe(document.body.querySelector('[role="tooltip"]')?.id);

    trigger?.dispatchEvent(new MouseEvent('mouseleave'));
    button?.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
    await nextTick();
    expect(document.body.querySelector('[role="tooltip"]')?.textContent).toBe('Copy Mainboard TTS');

    mounted.unmount();
  });

  test('supports disabled loading buttons and trailing badges', async () => {
    const onClick = vi.fn();
    const mounted = await mountAction(
      {
        label: 'Saving deck',
        shortLabel: 'Save',
        variant: 'primary',
        disabled: true,
        iconClass: 'animate-spin',
        onClick,
      },
      () => h('span', { 'data-testid': 'badge' }, '2'),
    );
    const button = mounted.container.querySelector<HTMLButtonElement>('button');

    button?.click();
    expect(button?.disabled).toBe(true);
    expect(button?.querySelector('[data-testid="action-icon"]')?.classList.contains('animate-spin')).toBe(true);
    expect(button?.querySelector('[data-testid="badge"]')?.textContent).toBe('2');
    expect(onClick).not.toHaveBeenCalled();

    mounted.unmount();
  });

  test('exposes tab selection and uses the same fixed-height geometry', async () => {
    const onClick = vi.fn();
    const mounted = await mountAction({
      label: 'Card groups',
      shortLabel: 'Groups',
      variant: 'tab',
      active: true,
      onClick,
    });
    const button = mounted.container.querySelector<HTMLButtonElement>('button');

    button?.click();
    expect(button?.getAttribute('aria-pressed')).toBe('true');
    expect(button?.classList.contains('theme-tab')).toBe(true);
    expect(button?.classList.contains('theme-tab-active')).toBe(true);
    expect(button?.classList.contains('h-10')).toBe(true);
    expect(onClick).toHaveBeenCalledTimes(1);

    mounted.unmount();
  });
});
