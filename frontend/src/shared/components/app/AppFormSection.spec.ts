import { createApp, h, nextTick } from 'vue';
import { afterEach, describe, expect, test } from 'vitest';
import AppFormSection from '@/shared/components/app/AppFormSection.vue';

describe('AppFormSection', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('renders an accessible divider-labelled fieldset with shared spacing', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const app = createApp({
      render: () =>
        h(
          AppFormSection,
          {
            title: 'Visibility',
            description: 'Choose who can view this deck.',
            class: 'custom-section',
          },
          { default: () => h('button', 'Private') },
        ),
    });
    app.mount(container);
    await nextTick();

    const fieldset = container.querySelector('fieldset');
    const legend = fieldset?.querySelector('legend');
    const description = fieldset?.querySelector('p');
    const content = fieldset?.querySelector('.app-form-section-content');
    expect(fieldset?.classList.contains('theme-divider')).toBe(true);
    expect(fieldset?.classList.contains('border-t')).toBe(true);
    expect(fieldset?.classList.contains('custom-section')).toBe(true);
    expect(legend?.textContent?.trim()).toBe('Visibility');
    expect(legend?.classList.contains('pr-2')).toBe(true);
    expect(description?.classList.contains('mt-1')).toBe(true);
    expect(fieldset?.getAttribute('aria-describedby')).toBe(description?.id);
    expect(content?.classList.contains('mt-4')).toBe(true);
    expect(content?.textContent).toContain('Private');

    app.unmount();
  });
});
