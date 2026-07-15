import { createApp, defineComponent, h, nextTick, ref } from 'vue';
import { afterEach, describe, expect, test } from 'vitest';
import DeckManaTypeGroupsDialog from '@/modules/decks/components/DeckManaTypeGroupsDialog.vue';
import type { ManaTypeGroup } from '@/composables/decks/manaDistribution';

const types = [
  { id: 'type-spell', key: 'spell', label: 'Spell' },
  { id: 'type-follower', key: 'follower', label: 'Follower' },
  { id: 'type-mana', key: 'mana', label: 'Mana' },
];

const mountDialog = async (initialGroups: ManaTypeGroup[] = []) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const open = ref(true);
  const sourceGroups = ref(initialGroups);
  const savedGroups = ref<ManaTypeGroup[] | null>(null);
  const closeCount = ref(0);

  const Wrapper = defineComponent({
    setup() {
      return () => h(DeckManaTypeGroupsDialog, {
        open: open.value,
        groups: sourceGroups.value,
        types,
        onClose: () => {
          closeCount.value += 1;
          open.value = false;
        },
        onSave: (groups: ManaTypeGroup[]) => {
          savedGroups.value = groups;
          open.value = false;
        },
      });
    },
  });

  const app = createApp(Wrapper);
  app.mount(container);
  await nextTick();

  return {
    container,
    sourceGroups,
    savedGroups,
    closeCount,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

const buttonByText = (container: HTMLElement, text: string): HTMLButtonElement => {
  const button = Array.from(container.querySelectorAll('button')).find((candidate) => candidate.textContent?.trim() === text);
  if (!(button instanceof HTMLButtonElement)) {
    throw new Error(`expected ${text} button`);
  }
  return button;
};

describe('DeckManaTypeGroupsDialog', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('keeps edits in a draft until save and discards them on cancel', async () => {
    const mounted = await mountDialog([{ id: 'spells', name: 'Spells', typeKeys: ['spell'] }]);
    const input = mounted.container.querySelector('input');
    if (!(input instanceof HTMLInputElement)) {
      throw new Error('expected group name input');
    }
    input.value = 'Changed';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await nextTick();
    buttonByText(mounted.container, 'Cancel').click();
    await nextTick();

    expect(mounted.sourceGroups.value).toEqual([{ id: 'spells', name: 'Spells', typeKeys: ['spell'] }]);
    expect(mounted.savedGroups.value).toBeNull();
    expect(mounted.closeCount.value).toBe(1);
    mounted.unmount();
  });

  test('validates and saves a named group while excluding the Mana type', async () => {
    const mounted = await mountDialog();
    expect(Array.from(mounted.container.querySelectorAll('button')).some((button) => button.textContent?.trim() === 'Mana')).toBe(false);

    buttonByText(mounted.container, 'Add group').click();
    await nextTick();
    const saveButton = buttonByText(mounted.container, 'Save groups');
    expect(saveButton.disabled).toBe(true);

    const input = mounted.container.querySelector('input');
    if (!(input instanceof HTMLInputElement)) {
      throw new Error('expected group name input');
    }
    input.value = 'Actions';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    buttonByText(mounted.container, 'Spell').click();
    await nextTick();

    expect(saveButton.disabled).toBe(false);
    saveButton.click();
    await nextTick();
    expect(mounted.savedGroups.value).toEqual([
      expect.objectContaining({ name: 'Actions', typeKeys: ['spell'] }),
    ]);
    mounted.unmount();
  });

  test('reorders groups and closes on Escape', async () => {
    const mounted = await mountDialog([
      { id: 'first', name: 'First', typeKeys: ['spell'] },
      { id: 'second', name: 'Second', typeKeys: ['follower'] },
    ]);
    const moveButton = mounted.container.querySelector('button[aria-label="Move Second up"]');
    if (!(moveButton instanceof HTMLButtonElement)) {
      throw new Error('expected move up button');
    }
    moveButton.click();
    await nextTick();
    buttonByText(mounted.container, 'Save groups').click();
    await nextTick();
    expect(mounted.savedGroups.value?.map((group) => group.id)).toEqual(['second', 'first']);
    mounted.unmount();

    const escapeMounted = await mountDialog();
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await nextTick();
    expect(escapeMounted.closeCount.value).toBe(1);
    escapeMounted.unmount();
  });
});
