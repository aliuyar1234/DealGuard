'use client';

import { useState, useCallback } from 'react';
import { useAuth } from './useAuth';
import {
  askLegalQuestion,
  getLegalConversations,
  getLegalConversation,
  deleteLegalConversation,
  LegalConversation,
  LegalMessage,
  Citation,
  AskQuestionResponse,
} from '@/lib/api/client';

interface UseLegalChatReturn {
  // State
  conversations: LegalConversation[];
  currentConversation: LegalConversation | null;
  messages: LegalMessage[];
  isLoading: boolean;
  isSending: boolean;
  error: string | null;

  // Actions
  loadConversations: () => Promise<void>;
  loadConversation: (conversationId: string) => Promise<void>;
  askQuestion: (question: string, conversationId?: string | null) => Promise<AskQuestionResponse | null>;
  deleteConversation: (conversationId: string) => Promise<void>;
  clearError: () => void;
  startNewConversation: () => void;
}

export function useLegalChat(): UseLegalChatReturn {
  const { token } = useAuth();
  const [conversations, setConversations] = useState<LegalConversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<LegalConversation | null>(null);
  const [messages, setMessages] = useState<LegalMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadConversations = useCallback(async () => {
    if (!token) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await getLegalConversations(token);
      setConversations(response.items);
    } catch (err) {
      setError('Gespräche konnten nicht geladen werden');
      console.error('Failed to load conversations:', err);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  const loadConversation = useCallback(async (conversationId: string) => {
    if (!token) return;

    setIsLoading(true);
    setError(null);

    try {
      const conversation = await getLegalConversation(conversationId, token);
      setCurrentConversation(conversation);
      setMessages(conversation.messages);
    } catch (err) {
      setError('Gespräch konnte nicht geladen werden');
      console.error('Failed to load conversation:', err);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  const askQuestion = useCallback(async (
    question: string,
    conversationId?: string | null
  ): Promise<AskQuestionResponse | null> => {
    if (!token) return null;

    setIsSending(true);
    setError(null);

    // Optimistically add user message
    const tempUserMessage: LegalMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: question,
      citations: [],
      confidence: null,
      requires_lawyer: false,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempUserMessage]);

    try {
      const response = await askLegalQuestion(
        question,
        conversationId || currentConversation?.id || null,
        token
      );

      // Add assistant response
      const assistantMessage: LegalMessage = {
        id: response.message_id,
        role: 'assistant',
        content: response.answer,
        citations: response.citations,
        confidence: response.confidence,
        requires_lawyer: response.requires_lawyer,
        created_at: new Date().toISOString(),
      };

      // Update messages (replace temp message with real one)
      setMessages(prev => [
        ...prev.filter(m => m.id !== tempUserMessage.id),
        { ...tempUserMessage, id: `user-${Date.now()}` },
        assistantMessage,
      ]);

      // Update current conversation if it's a new one
      if (!currentConversation || currentConversation.id !== response.conversation_id) {
        setCurrentConversation({
          id: response.conversation_id,
          title: question.substring(0, 50) + (question.length > 50 ? '...' : ''),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          messages: [],
        });
      }

      // Refresh conversations list
      loadConversations();

      return response;
    } catch (err) {
      // Remove optimistic message on error
      setMessages(prev => prev.filter(m => m.id !== tempUserMessage.id));
      setError('Frage konnte nicht beantwortet werden. Bitte versuchen Sie es erneut.');
      console.error('Failed to ask question:', err);
      return null;
    } finally {
      setIsSending(false);
    }
  }, [token, currentConversation, loadConversations]);

  const deleteConversation = useCallback(async (conversationId: string) => {
    if (!token) return;

    try {
      await deleteLegalConversation(conversationId, token);
      setConversations(prev => prev.filter(c => c.id !== conversationId));

      // Clear current if deleted
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
        setMessages([]);
      }
    } catch (err) {
      setError('Gespräch konnte nicht gelöscht werden');
      console.error('Failed to delete conversation:', err);
    }
  }, [token, currentConversation]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const startNewConversation = useCallback(() => {
    setCurrentConversation(null);
    setMessages([]);
  }, []);

  return {
    conversations,
    currentConversation,
    messages,
    isLoading,
    isSending,
    error,
    loadConversations,
    loadConversation,
    askQuestion,
    deleteConversation,
    clearError,
    startNewConversation,
  };
}
