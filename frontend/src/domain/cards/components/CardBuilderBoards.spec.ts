import { createApp, h, nextTick, reactive } from 'vue';
import { afterEach, expect, test, vi } from 'vitest';
import CardBuilderBoards from './CardBuilderBoards.vue';
const cleanups: Array<() => void> = [];
afterEach(() => cleanups.splice(0).forEach((cleanup) => cleanup()));
const mount = () => {
  const state = reactive({ activeBoardId: 'reserve', mainboardCount: 20, sideboards: [{ id: 'reserve', name: 'Reserve', totalCards: 3 }], locked: false });
  const actions = { onAdd: vi.fn(), onSelect: vi.fn(), onRename: vi.fn(), onRemove: vi.fn() };
  const target = document.createElement('div');
  document.body.appendChild(target);
  const app = createApp({ render: () => h(CardBuilderBoards, { ...state, ...actions }) });
  app.mount(target);
  cleanups.push(() => { app.unmount(); target.remove(); });
  return { state, actions, target };
};
const click = async (label: string) => {
  const button = [...document.querySelectorAll('button')].find((element) => element.textContent?.trim() === label || element.getAttribute('aria-label') === label);
  expect(button).toBeDefined();
  button!.click();
  await nextTick();
};
test('shared board controls add, switch and rename without changing quantities', async () => {
  const { actions, target } = mount();
  await click('Add Sideboard');
  expect(actions.onAdd).toHaveBeenCalledOnce();
  await click('Mainboard (20)');
  expect(actions.onSelect).toHaveBeenCalledWith('mainboard');
  await click('Open sideboard actions for Reserve');
  await click('Rename');
  const input = target.querySelector('input')!;
  input.value = 'Reinforcements';
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
  await nextTick();
  expect(actions.onRename).toHaveBeenCalledWith('reserve', 'Reinforcements');
});
test('locking during a sideboard action closes it and prevents edits', async () => {
  const { state, actions, target } = mount();
  await click('Open sideboard actions for Reserve');
  await click('Rename');
  expect(target.querySelector('input')).not.toBeNull();
  state.locked = true;
  await nextTick();
  expect(target.querySelector('input')).toBeNull();
  await click('Add Sideboard');
  expect(actions.onAdd).not.toHaveBeenCalled();
  expect(actions.onRename).not.toHaveBeenCalled();
});
