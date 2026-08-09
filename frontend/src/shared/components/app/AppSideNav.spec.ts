import { createApp, h, nextTick } from 'vue';
import { afterEach, describe, expect, test } from 'vitest';
import AppSideNav from '@/shared/components/app/AppSideNav.vue';

describe('AppSideNav', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('labels its navigation and supports mobile and after content', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const app = createApp({
      render: () =>
        h(
          AppSideNav,
          {
            title: 'Queues',
            description: 'Choose a queue.',
            navigationLabel: 'Operations queues',
            listClass: 'custom-list',
          },
          {
            mobile: () => h('select', { 'data-testid': 'mobile-select' }),
            default: () => h('button', 'Queue'),
            after: () => h('p', { 'data-testid': 'updated' }, 'Updated now'),
          },
        ),
    });
    app.mount(container);
    await nextTick();

    const nav = container.querySelector('nav');
    expect(container.textContent).toContain('Queues');
    expect(container.textContent).toContain('Choose a queue.');
    expect(nav?.getAttribute('aria-label')).toBe('Operations queues');
    expect(nav?.classList.contains('custom-list')).toBe(true);
    expect(container.querySelector('[data-testid="mobile-select"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="updated"]')?.textContent).toBe('Updated now');

    app.unmount();
    container.remove();
  });
});
