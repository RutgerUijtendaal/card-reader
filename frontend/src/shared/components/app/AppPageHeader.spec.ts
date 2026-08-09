/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, describe, expect, test } from 'vitest';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';

const TestIcon = defineComponent({
  setup() {
    return () => h('span');
  },
});

const mountHeader = async (subtitle?: string, subtitleSlot?: () => ReturnType<typeof h>) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const Root = defineComponent({
    setup() {
      return () =>
        h(
          AppPageHeader,
          {
            icon: TestIcon,
            title: 'Deck title',
            subtitle,
          },
          subtitleSlot ? { subtitle: subtitleSlot } : undefined,
        );
    },
  });
  const app = createApp(Root);
  app.mount(container);
  await nextTick();

  return {
    container,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('AppPageHeader', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('centers title content without reserving an empty subtitle row', async () => {
    const mounted = await mountHeader();
    const primary = mounted.container.querySelector('.app-page-header-primary');

    expect(primary?.classList.contains('items-center')).toBe(true);
    expect(primary?.classList.contains('items-start')).toBe(false);
    expect(mounted.container.querySelector('.theme-section-muted')).toBeNull();

    mounted.unmount();
  });

  test('keeps title content top-aligned when a subtitle is present', async () => {
    const mounted = await mountHeader('Supporting description');
    const primary = mounted.container.querySelector('.app-page-header-primary');

    expect(primary?.classList.contains('items-start')).toBe(true);
    expect(primary?.classList.contains('items-center')).toBe(false);
    expect(mounted.container.querySelector('.theme-section-muted')?.textContent).toBe('Supporting description');

    mounted.unmount();
  });

  test('renders custom subtitle content in the subtitle row', async () => {
    const mounted = await mountHeader(undefined, () => h('span', { 'data-testid': 'tag' }, 'Control'));
    const primary = mounted.container.querySelector('.app-page-header-primary');

    expect(primary?.classList.contains('items-start')).toBe(true);
    expect(mounted.container.querySelector('.theme-section-muted [data-testid="tag"]')?.textContent).toBe('Control');

    mounted.unmount();
  });

  test('renders contextual back navigation with a compact visible label', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div />' } },
        { path: '/cards', component: { template: '<div />' } },
      ],
    });
    await router.push('/');
    await router.isReady();
    const Root = defineComponent({
      setup() {
        return () => h(AppPageHeader, {
          icon: TestIcon,
          title: 'Card title',
          backTo: '/cards',
          backLabel: 'Back to Gallery',
        });
      },
    });
    const app = createApp(Root);
    app.use(router);
    app.mount(container);
    await nextTick();

    const backLink = container.querySelector<HTMLAnchorElement>('a[aria-label="Back to Gallery"]');
    expect(backLink?.textContent).toBe('Back');
    expect(backLink?.getAttribute('href')).toBe('/cards');
    expect(backLink?.classList.contains('h-10')).toBe(true);

    app.unmount();
    container.remove();
  });

  test('renders optional navigation in the center of the main header row', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const Root = defineComponent({
      setup() {
        return () => h(
          AppPageHeader,
          { icon: TestIcon, title: 'Deck title' },
          {
            center: () => h('nav', { 'aria-label': 'Deck sections' }, 'Sections'),
          },
        );
      },
    });
    const app = createApp(Root);
    app.mount(container);
    await nextTick();

    const navigation = container.querySelector('nav[aria-label="Deck sections"]');
    expect(navigation).not.toBeNull();
    expect(navigation?.parentElement?.classList.contains('app-page-header-center')).toBe(true);
    expect(navigation?.closest('.theme-subheader-row')).toBeNull();

    app.unmount();
    container.remove();
  });
});
