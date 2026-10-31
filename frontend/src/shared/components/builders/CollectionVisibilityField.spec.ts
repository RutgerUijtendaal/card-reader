import { createApp, nextTick } from 'vue';
import { expect, test, vi } from 'vitest';
import CollectionVisibilityField from './CollectionVisibilityField.vue';

test('shared visibility choices preserve labels, selection and feature-specific descriptions', async () => {
  const target = document.createElement('div');
  const update = vi.fn();
  const app = createApp(CollectionVisibilityField, {
    modelValue: 'private',
    descriptions: {
      private: 'Only you and staff.',
      unlisted: 'Anyone with the link.',
      public: 'Discoverable.',
    },
    'onUpdate:modelValue': update,
  });
  app.mount(target);
  try {
    expect(target.textContent).toContain('Only you and staff.');
    const buttons = Array.from(target.querySelectorAll('button'));
    expect(buttons.map((button) => button.textContent?.trim())).toEqual([
      'Private',
      'Unlisted',
      'Public',
    ]);
    buttons[1].click();
    await nextTick();
    expect(update).toHaveBeenCalledWith('unlisted');
  } finally {
    app.unmount();
  }
});
