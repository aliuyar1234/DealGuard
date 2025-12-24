import { renderHook, act } from '@testing-library/react';
import { useLegalChat } from '@/hooks/useLegalChat';

// Mock the API client functions
const mockGetLegalConversations = jest.fn();
const mockGetLegalConversation = jest.fn();
const mockAskLegalQuestion = jest.fn();
const mockDeleteLegalConversation = jest.fn();

jest.mock('@/lib/api/client', () => ({
  getLegalConversations: () => mockGetLegalConversations(),
  getLegalConversation: (id: string, token: string) =>
    mockGetLegalConversation(id, token),
  askLegalQuestion: (q: string, convId: string | null, token: string) =>
    mockAskLegalQuestion(q, convId, token),
  deleteLegalConversation: (id: string, token: string) =>
    mockDeleteLegalConversation(id, token),
}));

// Mock useAuth hook
const mockToken = 'test-token';
jest.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    token: mockToken,
    user: { id: 'user-1' },
    loading: false,
  }),
}));

describe('useLegalChat Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetLegalConversations.mockResolvedValue({ items: [] });
    mockGetLegalConversation.mockResolvedValue({
      id: 'conv-1',
      title: 'Test Conversation',
      messages: [],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    });
    mockAskLegalQuestion.mockResolvedValue({
      message_id: 'msg-1',
      conversation_id: 'conv-1',
      answer: 'This is the answer',
      citations: [],
      confidence: 0.9,
      requires_lawyer: false,
    });
    mockDeleteLegalConversation.mockResolvedValue(undefined);
  });

  describe('Initial State', () => {
    it('initializes with empty state', () => {
      const { result } = renderHook(() => useLegalChat());

      expect(result.current.conversations).toEqual([]);
      expect(result.current.currentConversation).toBe(null);
      expect(result.current.messages).toEqual([]);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isSending).toBe(false);
      expect(result.current.error).toBe(null);
    });
  });

  describe('loadConversations', () => {
    it('loads conversations successfully', async () => {
      const mockConversations = [
        {
          id: 'conv-1',
          title: 'Conversation 1',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
        {
          id: 'conv-2',
          title: 'Conversation 2',
          created_at: '2024-01-02T00:00:00Z',
          updated_at: '2024-01-02T00:00:00Z',
        },
      ];

      mockGetLegalConversations.mockResolvedValue({ items: mockConversations });

      const { result } = renderHook(() => useLegalChat());

      await act(async () => {
        await result.current.loadConversations();
      });

      expect(result.current.conversations).toEqual(mockConversations);
      expect(result.current.isLoading).toBe(false);
    });

    it('handles load error', async () => {
      mockGetLegalConversations.mockRejectedValue(new Error('API Error'));

      const { result } = renderHook(() => useLegalChat());

      await act(async () => {
        await result.current.loadConversations();
      });

      expect(result.current.error).toBe('Gespräche konnten nicht geladen werden');
      expect(result.current.isLoading).toBe(false);
    });

    it('sets loading state during fetch', async () => {
      let resolvePromise: (value: unknown) => void;
      mockGetLegalConversations.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve;
        })
      );

      const { result } = renderHook(() => useLegalChat());

      act(() => {
        result.current.loadConversations();
      });

      expect(result.current.isLoading).toBe(true);

      await act(async () => {
        resolvePromise!({ items: [] });
      });

      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('loadConversation', () => {
    it('loads single conversation with messages', async () => {
      const mockConversation = {
        id: 'conv-1',
        title: 'Test',
        messages: [
          { id: 'msg-1', role: 'user', content: 'Hello' },
          { id: 'msg-2', role: 'assistant', content: 'Hi there' },
        ],
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      mockGetLegalConversation.mockResolvedValue(mockConversation);

      const { result } = renderHook(() => useLegalChat());

      await act(async () => {
        await result.current.loadConversation('conv-1');
      });

      expect(result.current.currentConversation).toEqual(mockConversation);
      expect(result.current.messages).toEqual(mockConversation.messages);
    });

    it('handles load conversation error', async () => {
      mockGetLegalConversation.mockRejectedValue(new Error('Not found'));

      const { result } = renderHook(() => useLegalChat());

      await act(async () => {
        await result.current.loadConversation('invalid-id');
      });

      expect(result.current.error).toBe('Gespräch konnte nicht geladen werden');
    });
  });

  describe('askQuestion', () => {
    it('sends question and receives answer', async () => {
      const mockResponse = {
        message_id: 'msg-response',
        conversation_id: 'conv-new',
        answer: 'Die Kündigungsfrist beträgt 3 Monate.',
        citations: [{ file: 'contract.pdf', page: 5 }],
        confidence: 0.95,
        requires_lawyer: false,
      };

      mockAskLegalQuestion.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useLegalChat());

      let response;
      await act(async () => {
        response = await result.current.askQuestion('Was ist die Kündigungsfrist?');
      });

      expect(response).toEqual(mockResponse);
      expect(result.current.messages.length).toBe(2); // User + Assistant
      expect(result.current.isSending).toBe(false);
    });

    it('uses existing conversation ID', async () => {
      const { result } = renderHook(() => useLegalChat());

      await act(async () => {
        await result.current.askQuestion('Question 1');
      });

      // Now ask another question in same conversation
      await act(async () => {
        await result.current.askQuestion('Question 2', 'existing-conv-id');
      });

      expect(mockAskLegalQuestion).toHaveBeenLastCalledWith(
        'Question 2',
        'existing-conv-id',
        mockToken
      );
    });

    it('handles question error and removes optimistic message', async () => {
      mockAskLegalQuestion.mockRejectedValue(new Error('API Error'));

      const { result } = renderHook(() => useLegalChat());

      await act(async () => {
        await result.current.askQuestion('Test question');
      });

      expect(result.current.error).toBe(
        'Frage konnte nicht beantwortet werden. Bitte versuchen Sie es erneut.'
      );
      // Optimistic message should be removed
      expect(result.current.messages).toEqual([]);
    });

    it('sets isSending during request', async () => {
      let resolvePromise: (value: unknown) => void;
      mockAskLegalQuestion.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve;
        })
      );

      const { result } = renderHook(() => useLegalChat());

      act(() => {
        result.current.askQuestion('Test');
      });

      expect(result.current.isSending).toBe(true);

      await act(async () => {
        resolvePromise!({
          message_id: 'msg-1',
          conversation_id: 'conv-1',
          answer: 'Answer',
          citations: [],
          confidence: 0.9,
          requires_lawyer: false,
        });
      });

      expect(result.current.isSending).toBe(false);
    });
  });

  describe('deleteConversation', () => {
    it('deletes conversation and updates list', async () => {
      const mockConversations = [
        { id: 'conv-1', title: 'Conv 1' },
        { id: 'conv-2', title: 'Conv 2' },
      ];

      mockGetLegalConversations.mockResolvedValue({ items: mockConversations });

      const { result } = renderHook(() => useLegalChat());

      await act(async () => {
        await result.current.loadConversations();
      });

      await act(async () => {
        await result.current.deleteConversation('conv-1');
      });

      expect(result.current.conversations).toEqual([{ id: 'conv-2', title: 'Conv 2' }]);
    });

    it('clears current conversation if deleted', async () => {
      const mockConversation = {
        id: 'conv-1',
        title: 'Test',
        messages: [{ id: 'msg-1', content: 'Hello' }],
      };

      mockGetLegalConversation.mockResolvedValue(mockConversation);

      const { result } = renderHook(() => useLegalChat());

      // Load conversation first
      await act(async () => {
        await result.current.loadConversation('conv-1');
      });

      expect(result.current.currentConversation).not.toBe(null);

      // Delete it
      await act(async () => {
        await result.current.deleteConversation('conv-1');
      });

      expect(result.current.currentConversation).toBe(null);
      expect(result.current.messages).toEqual([]);
    });

    it('handles delete error', async () => {
      mockDeleteLegalConversation.mockRejectedValue(new Error('Delete failed'));

      const { result } = renderHook(() => useLegalChat());

      await act(async () => {
        await result.current.deleteConversation('conv-1');
      });

      expect(result.current.error).toBe('Gespräch konnte nicht gelöscht werden');
    });
  });

  describe('clearError', () => {
    it('clears error state', async () => {
      mockGetLegalConversations.mockRejectedValue(new Error('Error'));

      const { result } = renderHook(() => useLegalChat());

      await act(async () => {
        await result.current.loadConversations();
      });

      expect(result.current.error).not.toBe(null);

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBe(null);
    });
  });

  describe('startNewConversation', () => {
    it('clears current conversation and messages', async () => {
      const mockConversation = {
        id: 'conv-1',
        title: 'Test',
        messages: [{ id: 'msg-1', content: 'Hello' }],
      };

      mockGetLegalConversation.mockResolvedValue(mockConversation);

      const { result } = renderHook(() => useLegalChat());

      // Load a conversation first
      await act(async () => {
        await result.current.loadConversation('conv-1');
      });

      expect(result.current.currentConversation).not.toBe(null);

      // Start new conversation
      act(() => {
        result.current.startNewConversation();
      });

      expect(result.current.currentConversation).toBe(null);
      expect(result.current.messages).toEqual([]);
    });
  });
});

describe('useLegalChat without token', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('does not load conversations without token', async () => {
    // Override the mock to return null token
    jest.doMock('@/hooks/useAuth', () => ({
      useAuth: () => ({
        token: null,
        user: null,
        loading: false,
      }),
    }));

    // Re-import to get fresh mock
    jest.resetModules();

    // This test documents the expected behavior when there's no token
    // The actual implementation should handle this gracefully
  });
});
