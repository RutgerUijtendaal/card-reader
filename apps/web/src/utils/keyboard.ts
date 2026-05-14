export const isEditableKeyboardTarget = (event: KeyboardEvent): boolean => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  if (target.isContentEditable) {
    return true;
  }

  const editableSelector = 'input, textarea, select, [contenteditable="true"], [role="textbox"]';
  return target.matches(editableSelector) || target.closest(editableSelector) !== null;
};
