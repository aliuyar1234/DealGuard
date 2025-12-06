'use client';

import { useEffect, useRef, useState } from 'react';
import { Shell } from '@/components/layout/Shell';
import { Button } from '@/components/ui/Button';
import { useLegalChat } from '@/hooks/useLegalChat';
import { ChatMessage } from '@/components/legal/ChatMessage';

export default function JuristPage() {
  const {
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
  } = useLegalChat();

  const [input, setInput] = useState('');
  const [showSidebar, setShowSidebar] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSending) return;

    const question = input.trim();
    setInput('');
    await askQuestion(question);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <Shell>
      <div className="flex h-[calc(100vh-4rem)]">
        {/* Sidebar - Conversation List */}
        {showSidebar && (
          <aside className="w-64 border-r border-gray-200 bg-gray-50 flex flex-col">
            <div className="p-4 border-b border-gray-200">
              <Button
                onClick={startNewConversation}
                className="w-full"
              >
                + Neues Gespräch
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto">
              {conversations.length === 0 ? (
                <p className="p-4 text-sm text-gray-500 text-center">
                  Keine Gespräche
                </p>
              ) : (
                <ul className="divide-y divide-gray-200">
                  {conversations.map((conv) => (
                    <li key={conv.id}>
                      <button
                        onClick={() => loadConversation(conv.id)}
                        className={`w-full px-4 py-3 text-left hover:bg-gray-100 transition-colors ${
                          currentConversation?.id === conv.id ? 'bg-blue-50' : ''
                        }`}
                      >
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {conv.title || 'Untitled'}
                        </p>
                        <p className="text-xs text-gray-500">
                          {new Date(conv.updated_at).toLocaleDateString('de-AT')}
                        </p>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </aside>
        )}

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col bg-gray-100">
          {/* Header */}
          <header className="px-4 py-3 bg-white border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowSidebar(!showSidebar)}
                className="p-1 text-gray-500 hover:text-gray-700"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  AI-Jurist
                </h1>
                <p className="text-xs text-gray-500">
                  Fragen Sie zu Ihren Verträgen
                </p>
              </div>
            </div>

            {currentConversation && (
              <button
                onClick={() => {
                  if (confirm('Gespräch wirklich löschen?')) {
                    deleteConversation(currentConversation.id);
                  }
                }}
                className="p-2 text-gray-400 hover:text-red-500 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}
          </header>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <EmptyState />
            ) : (
              <>
                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
                {isSending && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" />
                        <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce [animation-delay:0.2s]" />
                        <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce [animation-delay:0.4s]" />
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Error message */}
          {error && (
            <div className="mx-4 mb-2 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between">
              <p className="text-sm text-red-700">{error}</p>
              <button onClick={clearError} className="text-red-500 hover:text-red-700">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          )}

          {/* Input */}
          <form onSubmit={handleSubmit} className="p-4 bg-white border-t border-gray-200">
            <div className="flex gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Fragen Sie zu Ihren Verträgen... (Enter zum Senden, Shift+Enter für neue Zeile)"
                className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                rows={1}
                disabled={isSending}
              />
              <Button
                type="submit"
                disabled={!input.trim() || isSending}
                className="self-end"
              >
                {isSending ? (
                  <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                )}
              </Button>
            </div>
            <p className="mt-2 text-xs text-gray-500">
              Der AI-Jurist durchsucht Ihre Verträge und zitiert Quellen. Für komplexe Rechtsfragen konsultieren Sie bitte einen Anwalt.
            </p>
          </form>
        </div>
      </div>
    </Shell>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <div className="w-16 h-16 mb-4 bg-blue-100 rounded-full flex items-center justify-center">
        <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-gray-900 mb-2">
        Willkommen beim AI-Jurist
      </h2>
      <p className="text-sm text-gray-600 max-w-md mb-6">
        Stellen Sie Fragen zu Ihren hochgeladenen Verträgen. Der AI-Jurist durchsucht Ihre Dokumente und gibt Antworten mit Quellenangaben.
      </p>

      <div className="grid gap-2 text-left max-w-md">
        <SuggestionButton text="Welche Kündigungsfristen habe ich?" />
        <SuggestionButton text="Gibt es Haftungsbeschränkungen in meinen Verträgen?" />
        <SuggestionButton text="Was sind die Zahlungsbedingungen bei meinen Lieferanten?" />
      </div>
    </div>
  );
}

function SuggestionButton({ text }: { text: string }) {
  const { askQuestion, isSending } = useLegalChat();

  return (
    <button
      onClick={() => askQuestion(text)}
      disabled={isSending}
      className="text-left px-4 py-3 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors disabled:opacity-50"
    >
      {text}
    </button>
  );
}
