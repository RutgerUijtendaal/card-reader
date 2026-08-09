import { describe, expect, test } from 'vitest';
import {
  canCreateFromPersistenceState,
  isDeckMutationLocked,
  transitionDeckCreation,
  transitionDeckDraftPersistence,
  type DeckCreationState,
  type DeckDraftPersistenceState,
} from '@/features/decks/utils/deckEditorLifecycle';

describe('deckEditorLifecycle', () => {
  test.each([
    ['checking', 'recovery'],
    ['checking', 'synced'],
    ['checking', 'memory-only'],
    ['checking', 'conflict'],
    ['recovery', 'synced'],
    ['recovery', 'memory-only'],
    ['recovery', 'conflict'],
    ['synced', 'synced'],
    ['synced', 'memory-only'],
    ['synced', 'conflict'],
    ['memory-only', 'memory-only'],
    ['memory-only', 'synced'],
    ['memory-only', 'conflict'],
    ['conflict', 'conflict'],
    ['conflict', 'recovery'],
    ['conflict', 'synced'],
    ['conflict', 'memory-only'],
  ] as const)('allows persistence transition %s -> %s', (from, to) => {
    expect(transitionDeckDraftPersistence({ status: from }, { status: to })).toEqual({ status: to });
  });

  test.each([
    ['recovery', 'checking'],
    ['synced', 'checking'],
    ['memory-only', 'recovery'],
    ['conflict', 'checking'],
  ] as const)('rejects persistence transition %s -> %s', (from, to) => {
    expect(() => transitionDeckDraftPersistence({ status: from }, { status: to })).toThrow();
  });

  test.each([
    ['idle', 'idle'],
    ['idle', 'creating'],
    ['idle', 'unknown'],
    ['creating', 'idle'],
    ['creating', 'unknown'],
    ['unknown', 'creating'],
    ['unknown', 'unknown'],
    ['unknown', 'idle'],
  ] as const)('allows creation transition %s -> %s', (from, to) => {
    expect(transitionDeckCreation({ status: from }, { status: to })).toEqual({ status: to });
  });

  test.each([
    ['creating', 'creating'],
  ] as const)('rejects creation transition %s -> %s', (from, to) => {
    expect(() => transitionDeckCreation({ status: from }, { status: to })).toThrow();
  });

  test('derives creation and mutation permissions from both axes', () => {
    const states: DeckDraftPersistenceState[] = [
      { status: 'checking' },
      { status: 'recovery' },
      { status: 'synced' },
      { status: 'memory-only' },
      { status: 'conflict' },
    ];
    const idle: DeckCreationState = { status: 'idle' };
    expect(states.map((state) => canCreateFromPersistenceState(state))).toEqual([
      false, false, true, true, false,
    ]);
    expect(states.map((state) => isDeckMutationLocked(state, idle))).toEqual([
      true, true, false, false, true,
    ]);
    expect(isDeckMutationLocked({ status: 'synced' }, { status: 'creating' })).toBe(true);
    expect(isDeckMutationLocked({ status: 'memory-only' }, { status: 'unknown' })).toBe(true);
  });
});
