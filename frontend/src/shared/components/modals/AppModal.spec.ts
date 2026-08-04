import { createApp, defineComponent, h, nextTick, ref } from 'vue';
import { afterEach, describe, expect, test } from 'vitest';
import AppModal from '@/shared/components/modals/AppModal.vue';

const mountModal = async (options: { closeDisabled?: boolean } = {}) => {
  const container = document.createElement('div');
  const trigger = document.createElement('button');
  trigger.textContent = 'Open';
  document.body.append(trigger, container);
  trigger.focus();

  const open = ref(true);
  const closeCount = ref(0);
  const app = createApp(
    defineComponent({
      setup() {
        return () =>
          h(
            AppModal,
            {
              open: open.value,
              ariaLabelledby: 'test-modal-title',
              closeDisabled: options.closeDisabled,
              onClose: () => {
                closeCount.value += 1;
                open.value = false;
              },
            },
            {
              default: () => [
                h('h2', { id: 'test-modal-title' }, 'Test modal'),
                h('button', { type: 'button' }, 'First'),
                h('button', { type: 'button' }, 'Last'),
              ],
            },
          );
      },
    }),
  );
  app.mount(container);
  await nextTick();

  return {
    app,
    container,
    trigger,
    open,
    closeCount,
  };
};

describe('AppModal', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('teleports to the body, traps focus, and restores the trigger focus', async () => {
    const mounted = await mountModal();
    const dialog = document.body.querySelector('[role="dialog"]');
    expect(dialog).toBeInstanceOf(HTMLElement);
    expect(mounted.container.querySelector('[role="dialog"]')).toBeNull();

    const buttons = Array.from(dialog?.querySelectorAll('button') ?? []);
    const first = buttons[0] as HTMLButtonElement;
    const last = buttons[1] as HTMLButtonElement;
    last.focus();
    last.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }));
    expect(document.activeElement).toBe(first);

    first.focus();
    first.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true }),
    );
    expect(document.activeElement).toBe(last);

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await nextTick();
    await nextTick();
    expect(mounted.closeCount.value).toBe(1);
    expect(document.activeElement).toBe(mounted.trigger);
    mounted.app.unmount();
  });

  test('closes from the overlay unless closing is disabled', async () => {
    const mounted = await mountModal();
    const dialog = document.body.querySelector('[role="dialog"]');
    dialog?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await nextTick();
    expect(mounted.closeCount.value).toBe(1);
    mounted.app.unmount();

    const disabled = await mountModal({ closeDisabled: true });
    const disabledDialog = document.body.querySelector('[role="dialog"]');
    disabledDialog?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await nextTick();
    expect(disabled.closeCount.value).toBe(0);
    disabled.app.unmount();
  });
});
