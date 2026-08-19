import { createApp, h, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import AppSelect from '@/shared/components/app/AppSelect.vue';

describe('AppSelect', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('rotates the chevron glyph around its own center and emits the selected value', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const updateModelValue = vi.fn();
    const app = createApp({
      render: () =>
        h(AppSelect, {
          modelValue: 'player',
          options: [
            { value: 'player', label: 'Player' },
            { value: 'evil', label: 'Evil' },
          ],
          'onUpdate:modelValue': updateModelValue,
        }),
    });
    app.mount(container);
    await nextTick();

    const select = container.querySelector('select');
    const chevronWrapper = container.querySelector('.app-select-chevron');
    const chevron = chevronWrapper?.querySelector('svg');
    expect(select).toBeInstanceOf(HTMLSelectElement);
    expect(chevronWrapper?.classList.contains('rotate-180')).toBe(false);
    expect(chevron?.classList.contains('origin-center')).toBe(true);
    expect(chevron?.classList.contains('rotate-180')).toBe(false);

    select?.dispatchEvent(new Event('pointerdown', { bubbles: true }));
    await nextTick();
    expect(chevron?.classList.contains('rotate-180')).toBe(true);

    (select as HTMLSelectElement).value = 'evil';
    select?.dispatchEvent(new Event('change', { bubbles: true }));
    await nextTick();
    expect(chevron?.classList.contains('rotate-180')).toBe(false);
    expect(updateModelValue).toHaveBeenCalledWith('evil');

    app.unmount();
  });
});
