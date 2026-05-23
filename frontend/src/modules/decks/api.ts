import { api } from '@/api/client';
import type { DeckRecord, DeckUpsertRequest } from '@/modules/decks/types';

export const fetchPublicDecks = async (): Promise<DeckRecord[]> => {
  const response = await api.get<DeckRecord[]>('/decks');
  return response.data;
};

export const fetchDeckDetail = async (deckId: string): Promise<DeckRecord> => {
  const response = await api.get<DeckRecord>(`/decks/${deckId}`);
  return response.data;
};

export const fetchMyDecks = async (): Promise<DeckRecord[]> => {
  const response = await api.get<DeckRecord[]>('/my/decks');
  return response.data;
};

export const fetchMyDeck = async (deckId: string): Promise<DeckRecord> => {
  const response = await api.get<DeckRecord>(`/my/decks/${deckId}`);
  return response.data;
};

export const createDeck = async (payload: DeckUpsertRequest): Promise<DeckRecord> => {
  const response = await api.post<DeckRecord>('/my/decks', payload);
  return response.data;
};

export const updateDeck = async (deckId: string, payload: DeckUpsertRequest): Promise<DeckRecord> => {
  const response = await api.patch<DeckRecord>(`/my/decks/${deckId}`, payload);
  return response.data;
};

export const deleteDeck = async (deckId: string): Promise<void> => {
  await api.delete(`/my/decks/${deckId}`);
};
