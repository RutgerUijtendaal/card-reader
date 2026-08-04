import { createApp, defineComponent, h, nextTick, ref } from 'vue';
import { afterEach, describe, expect, test } from 'vitest';
import DeckManaTypeGroupsDialog from '@/features/decks/components/DeckManaTypeGroupsDialog.vue';
import type { ManaTypeGroup } from '@/domain/decks/utils/manaDistribution';

const types = [
  { id: 'type-spell', key: 'spell', label: 'Spell' },
  { id: 'type-follower', key: 'follower', label: 'Follower' },
  { id: 'type-attachment', key: 'attachment', label: 'Attachment' },
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
    dialogRoot: document.body,
    sourceGroups,
    savedGroups,
    closeCount,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

const buttonByText = (container: ParentNode, text: string): HTMLButtonElement => {
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
    const mounted = await mountDialog([{
      id: 'spells',
      name: 'Spells',
      typeKeys: ['spell', 'attachment'],
      excludedTypeKeys: ['follower'],
      isVisible: true,
    }]);
    expect(mounted.container.querySelector('[role="dialog"]')).toBeNull();
    expect(mounted.dialogRoot.querySelector('[role="dialog"]')).not.toBeNull();
    expect(mounted.dialogRoot.querySelector('[data-testid="mana-type-group-summary-spells"]')).not.toBeNull();
    expect(mounted.dialogRoot.querySelector('input')).toBeNull();
    buttonByText(mounted.dialogRoot, 'Hide').click();
    buttonByText(mounted.dialogRoot, 'Edit').click();
    await nextTick();
    const input = mounted.dialogRoot.querySelector('input');
    if (!(input instanceof HTMLInputElement)) {
      throw new Error('expected group name input');
    }
    input.value = 'Changed';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await nextTick();
    buttonByText(mounted.dialogRoot, 'Cancel').click();
    await nextTick();

    expect(mounted.sourceGroups.value).toEqual([{
      id: 'spells',
      name: 'Spells',
      typeKeys: ['spell', 'attachment'],
      excludedTypeKeys: ['follower'],
      isVisible: true,
    }]);
    expect(mounted.savedGroups.value).toBeNull();
    expect(mounted.closeCount.value).toBe(1);
    mounted.unmount();
  });

  test('counts included and excluded types toward the two-active-rule requirement', async () => {
    const mounted = await mountDialog();
    expect(Array.from(mounted.dialogRoot.querySelectorAll('button')).some((button) => button.textContent?.trim() === 'Mana')).toBe(false);

    buttonByText(mounted.dialogRoot, 'Add group').click();
    await nextTick();
    const saveButton = buttonByText(mounted.dialogRoot, 'Save groups');
    expect(saveButton.disabled).toBe(true);

    const input = mounted.dialogRoot.querySelector('input');
    if (!(input instanceof HTMLInputElement)) {
      throw new Error('expected group name input');
    }
    input.value = 'Actions';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    buttonByText(mounted.dialogRoot, 'Spell').click();
    await nextTick();
    expect(saveButton.disabled).toBe(true);

    const followerButton = buttonByText(mounted.dialogRoot, 'Follower');
    followerButton.click();
    await nextTick();
    followerButton.click();
    await nextTick();

    expect(saveButton.disabled).toBe(false);
    saveButton.click();
    await nextTick();
    expect(mounted.savedGroups.value).toEqual([
      expect.objectContaining({
        name: 'Actions',
        typeKeys: ['spell'],
        excludedTypeKeys: ['follower'],
        isVisible: true,
      }),
    ]);
    mounted.unmount();
  });

  test('persists whether a collapsed group is displayed in the statistics list', async () => {
    const mounted = await mountDialog([{
      id: 'spells',
      name: 'Spells',
      typeKeys: ['spell', 'attachment'],
      excludedTypeKeys: ['follower'],
      isVisible: true,
    }]);

    expect(mounted.dialogRoot.textContent).toContain('+ Spell');
    expect(mounted.dialogRoot.textContent).toContain('− Follower');
    expect(mounted.dialogRoot.querySelector('.theme-choice-chip-include')?.textContent).toContain('Spell');
    expect(mounted.dialogRoot.querySelector('.theme-choice-chip-exclude')?.textContent).toContain('Follower');
    const visibilityStatus = mounted.dialogRoot.querySelector('[data-testid="mana-type-group-visibility-spells"]');
    expect(visibilityStatus?.classList.contains('theme-pill')).toBe(false);
    expect(visibilityStatus?.textContent).toContain('Shown in statistics');
    buttonByText(mounted.dialogRoot, 'Hide').click();
    await nextTick();
    expect(visibilityStatus?.textContent).toContain('Hidden from statistics');
    expect(buttonByText(mounted.dialogRoot, 'Display')).toBeInstanceOf(HTMLButtonElement);
    buttonByText(mounted.dialogRoot, 'Save groups').click();
    await nextTick();

    expect(mounted.savedGroups.value?.[0]?.isVisible).toBe(false);
    mounted.unmount();
  });

  test('applies enable, disable, and clear actions to every selectable type', async () => {
    const mounted = await mountDialog([{
      id: 'actions',
      name: 'Actions',
      typeKeys: ['spell', 'follower'],
      excludedTypeKeys: ['attachment'],
      isVisible: true,
    }]);
    const saveButton = buttonByText(mounted.dialogRoot, 'Save groups');
    buttonByText(mounted.dialogRoot, 'Edit').click();
    await nextTick();

    buttonByText(mounted.dialogRoot, 'Disable all').click();
    await nextTick();
    expect(mounted.dialogRoot.querySelectorAll('button[aria-label$="excluded. Click to clear."]')).toHaveLength(3);
    expect(saveButton.disabled).toBe(false);

    buttonByText(mounted.dialogRoot, 'Enable all').click();
    await nextTick();
    expect(mounted.dialogRoot.querySelectorAll('button[aria-label$="included. Click to exclude."]')).toHaveLength(3);
    expect(saveButton.disabled).toBe(false);

    buttonByText(mounted.dialogRoot, 'Clear all').click();
    await nextTick();
    expect(mounted.dialogRoot.querySelectorAll('button[aria-label$="not filtered. Click to include."]')).toHaveLength(3);
    expect(saveButton.disabled).toBe(true);
    mounted.unmount();
  });

  test('reorders groups and closes on Escape', async () => {
    const mounted = await mountDialog([
      {
        id: 'first',
        name: 'First',
        typeKeys: ['spell', 'attachment'],
        excludedTypeKeys: [],
        isVisible: true,
      },
      {
        id: 'second',
        name: 'Second',
        typeKeys: ['follower', 'attachment'],
        excludedTypeKeys: [],
        isVisible: true,
      },
    ]);
    const editSecondButton = mounted.dialogRoot.querySelector('button[aria-label="Edit Second"]');
    if (!(editSecondButton instanceof HTMLButtonElement)) {
      throw new Error('expected edit second button');
    }
    editSecondButton.click();
    await nextTick();
    const moveButton = mounted.dialogRoot.querySelector('button[aria-label="Move Second up"]');
    if (!(moveButton instanceof HTMLButtonElement)) {
      throw new Error('expected move up button');
    }
    moveButton.click();
    await nextTick();
    buttonByText(mounted.dialogRoot, 'Save groups').click();
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
