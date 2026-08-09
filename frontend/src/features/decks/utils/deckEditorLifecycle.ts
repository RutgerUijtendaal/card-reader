export type DeckDraftPersistenceState =
  | { status: 'checking' }
  | { status: 'recovery' }
  | { status: 'synced' }
  | { status: 'memory-only' }
  | { status: 'conflict' };

export type DeckCreationState =
  | { status: 'idle' }
  | { status: 'creating' }
  | { status: 'unknown' };

const persistenceTransitions: Record<
  DeckDraftPersistenceState['status'],
  ReadonlySet<DeckDraftPersistenceState['status']>
> = {
  checking: new Set(['recovery', 'synced', 'memory-only']),
  recovery: new Set(['synced', 'memory-only', 'conflict']),
  synced: new Set(['synced', 'memory-only', 'conflict']),
  'memory-only': new Set(['memory-only', 'synced', 'conflict']),
  conflict: new Set(['conflict', 'recovery', 'synced', 'memory-only']),
};

const creationTransitions: Record<
  DeckCreationState['status'],
  ReadonlySet<DeckCreationState['status']>
> = {
  idle: new Set(['idle', 'creating', 'unknown']),
  creating: new Set(['idle', 'unknown']),
  unknown: new Set(['idle', 'creating', 'unknown']),
};

const transition = <Status extends string>(
  axis: string,
  current: Status,
  next: Status,
  allowed: Record<Status, ReadonlySet<Status>>,
): Status => {
  if (!allowed[current].has(next)) {
    throw new Error(`Invalid ${axis} transition: ${current} -> ${next}`);
  }
  return next;
};

export const transitionDeckDraftPersistence = (
  current: DeckDraftPersistenceState,
  next: DeckDraftPersistenceState,
): DeckDraftPersistenceState => ({
  status: transition('draft persistence', current.status, next.status, persistenceTransitions),
});

export const transitionDeckCreation = (
  current: DeckCreationState,
  next: DeckCreationState,
): DeckCreationState => ({
  status: transition('deck creation', current.status, next.status, creationTransitions),
});

export const canCreateFromPersistenceState = (state: DeckDraftPersistenceState): boolean =>
  state.status === 'synced' || state.status === 'memory-only';

export const isDeckMutationLocked = (
  persistence: DeckDraftPersistenceState,
  creation: DeckCreationState,
): boolean => persistence.status === 'checking'
  || persistence.status === 'recovery'
  || persistence.status === 'conflict'
  || creation.status === 'creating'
  || creation.status === 'unknown';
