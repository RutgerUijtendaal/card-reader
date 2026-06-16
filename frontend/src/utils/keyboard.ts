export const isEditableKeyboardTarget = (event: KeyboardEvent): boolean => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  if (target.isContentEditable) {
    return true;
  }

  if (target instanceof HTMLInputElement) {
    const type = target.type.toLowerCase();
    return type === ''
      || [
        'date',
        'datetime-local',
        'email',
        'month',
        'number',
        'password',
        'search',
        'tel',
        'text',
        'time',
        'url',
        'week',
      ].includes(type);
  }

  const editableSelector = 'textarea, select, [contenteditable="true"], [role="textbox"]';
  return target.matches(editableSelector) || target.closest(editableSelector) !== null;
};
