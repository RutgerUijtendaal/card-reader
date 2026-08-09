/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick, type Component } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test, vi } from 'vitest';
import AppSideNavItem from '@/shared/components/app/AppSideNavItem.vue';

const TestIcon = defineComponent({
  setup() {
    return () => h('svg', { 'data-testid': 'side-nav-icon' });
  },
});

const mountItem = async (
  props: {
    label: string;
    description?: string;
    icon?: Component;
    to?: string;
    active?: boolean;
    disabled?: boolean;
    onClick?: (event: MouseEvent) => void;
  },
  slots?: {
    trailing?: () => ReturnType<typeof h>;
    meta?: () => ReturnType<typeof h>;
  },
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
  const app = createApp({
    render: () => h(AppSideNavItem, props, slots),
  });
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

describe('AppSideNavItem', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('renders an active route link with shared content and metadata slots', async () => {
    const mounted = await mountItem(
      {
        label: 'Display',
        description: 'Gallery preferences.',
        icon: TestIcon,
        to: '/target',
        active: true,
      },
      {
        trailing: () => h('span', { 'data-testid': 'trailing' }, 'Online'),
        meta: () => h('span', { 'data-testid': 'meta' }, 'Completed 2'),
      },
    );
    const link = mounted.container.querySelector<HTMLAnchorElement>('a');

    expect(link?.getAttribute('href')).toBe('/target');
    expect(link?.getAttribute('aria-current')).toBe('page');
    expect(link?.classList.contains('theme-selected-surface-strong')).toBe(true);
    expect(link?.classList.contains('focus-visible:ring-2')).toBe(true);
    expect(link?.querySelector('[data-testid="side-nav-icon"]')).not.toBeNull();
    expect(link?.querySelector('[data-testid="trailing"]')?.textContent).toBe('Online');
    expect(link?.querySelector('[data-testid="meta"]')?.textContent).toBe('Completed 2');

    mounted.unmount();
  });

  test('emits button clicks and exposes the inactive shared surface', async () => {
    const onClick = vi.fn();
    const mounted = await mountItem({ label: 'Flag reviews', onClick });
    const button = mounted.container.querySelector<HTMLButtonElement>('button');

    button?.click();
    expect(button?.type).toBe('button');
    expect(button?.classList.contains('theme-card-frame')).toBe(true);
    expect(button?.getAttribute('aria-current')).toBeNull();
    expect(onClick).toHaveBeenCalledOnce();

    mounted.unmount();
  });

  test('prevents disabled buttons and links from activating', async () => {
    const onButtonClick = vi.fn();
    const buttonMount = await mountItem({ label: 'Disabled button', disabled: true, onClick: onButtonClick });
    const button = buttonMount.container.querySelector<HTMLButtonElement>('button');
    button?.click();
    expect(button?.disabled).toBe(true);
    expect(button?.getAttribute('aria-disabled')).toBe('true');
    expect(onButtonClick).not.toHaveBeenCalled();
    buttonMount.unmount();

    const onLinkClick = vi.fn();
    const linkMount = await mountItem({
      label: 'Disabled link',
      to: '/target',
      disabled: true,
      onClick: onLinkClick,
    });
    const link = linkMount.container.querySelector<HTMLAnchorElement>('a');
    link?.click();
    await nextTick();
    expect(link?.getAttribute('aria-disabled')).toBe('true');
    expect(link?.getAttribute('tabindex')).toBe('-1');
    expect(linkMount.router.currentRoute.value.path).toBe('/');
    expect(onLinkClick).not.toHaveBeenCalled();
    linkMount.unmount();
  });
});
