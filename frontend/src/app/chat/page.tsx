'use client';

import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  sendChatMessage,
  type ChatMessage,
  type ChatResponse,
  type ToolCall,
} from '@/lib/api/client';
import { Send, Bot, User, Loader2, Wrench, AlertTriangle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
  isLoading?: boolean;
}

// Example prompts to show users
const EXAMPLE_PROMPTS = [
  'Welche Kündigungsfrist gilt laut ABGB für Mietverträge?',
  'Ist die Firma ABC GmbH insolvent?',
  'Welche Fristen habe ich in den nächsten 30 Tagen?',
  'Was sagt das UGB zur Geschäftsführerhaftung?',
];

export default function ChatPage() {
  const { token } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isLoading || !token) return;

    const userMessage = input.trim();
    setInput('');
    setError(null);

    // Add user message
    const newMessages: Message[] = [
      ...messages,
      { role: 'user', content: userMessage },
    ];
    setMessages([...newMessages, { role: 'assistant', content: '', isLoading: true }]);
    setIsLoading(true);

    try {
      // Convert to API format
      const apiMessages: ChatMessage[] = newMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // Send to API
      const response = await sendChatMessage(apiMessages, token);

      // Update with response
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          content: response.message,
          toolCalls: response.tool_calls || undefined,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ein Fehler ist aufgetreten');
      // Remove loading message
      setMessages(newMessages);
    } finally {
      setIsLoading(false);
    }
  }

  function handleExampleClick(prompt: string) {
    setInput(prompt);
    inputRef.current?.focus();
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-900">DealGuard AI</h1>
        <p className="text-gray-600">
          Ihr Rechtsassistent mit Zugang zu echten österreichischen Datenquellen
        </p>
      </div>

      {/* Chat Container */}
      <Card className="flex-1 flex flex-col overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            // Empty state
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <Bot className="w-16 h-16 text-primary-500 mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Willkommen bei DealGuard AI
              </h2>
              <p className="text-gray-600 mb-6 max-w-md">
                Ich habe Zugang zu echten österreichischen Datenquellen:
                RIS (Gesetze), Ediktsdatei (Insolvenzen), und Ihre Verträge.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-w-2xl">
                {EXAMPLE_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleExampleClick(prompt)}
                    className="p-3 text-left text-sm bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 transition-colors"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            // Messages list
            <>
              {messages.map((message, idx) => (
                <div
                  key={idx}
                  className={`flex gap-3 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.role === 'assistant' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                      {message.isLoading ? (
                        <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
                      ) : (
                        <Bot className="w-5 h-5 text-primary-600" />
                      )}
                    </div>
                  )}

                  <div
                    className={`max-w-[80%] rounded-lg p-4 ${
                      message.role === 'user'
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    {message.isLoading ? (
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500">Denke nach...</span>
                      </div>
                    ) : (
                      <>
                        {/* Tool calls indicator */}
                        {message.toolCalls && message.toolCalls.length > 0 && (
                          <div className="mb-3 pb-3 border-b border-gray-200">
                            <div className="flex items-center gap-1 text-xs text-gray-500 mb-1">
                              <Wrench className="w-3 h-3" />
                              <span>Verwendete Datenquellen:</span>
                            </div>
                            <div className="flex flex-wrap gap-1">
                              {message.toolCalls.map((tool, toolIdx) => (
                                <span
                                  key={toolIdx}
                                  className="inline-flex items-center px-2 py-0.5 text-xs bg-white rounded border border-gray-200"
                                >
                                  {tool.name === 'search_ris' && 'RIS (Gesetze)'}
                                  {tool.name === 'get_law_text' && 'Gesetzestext'}
                                  {tool.name === 'search_ediktsdatei' && 'Ediktsdatei'}
                                  {tool.name === 'search_contracts' && 'Verträge'}
                                  {tool.name === 'get_contract' && 'Vertrag'}
                                  {tool.name === 'get_partners' && 'Partner'}
                                  {tool.name === 'get_deadlines' && 'Fristen'}
                                  {tool.name === 'search_firmenbuch' && 'Firmenbuch'}
                                  {tool.name === 'get_firmenbuch_auszug' && 'Firmenbuch-Auszug'}
                                  {tool.name === 'check_company_austria' && 'Firmenprüfung'}
                                  {tool.name === 'check_sanctions' && 'Sanktionslisten'}
                                  {tool.name === 'check_pep' && 'PEP-Prüfung'}
                                  {tool.name === 'comprehensive_compliance_check' && 'Compliance-Check'}
                                  {!['search_ris', 'get_law_text', 'search_ediktsdatei', 'search_contracts', 'get_contract', 'get_partners', 'get_deadlines', 'search_firmenbuch', 'get_firmenbuch_auszug', 'check_company_austria', 'check_sanctions', 'check_pep', 'comprehensive_compliance_check'].includes(tool.name) && tool.name}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Message content with Markdown */}
                        <div className="prose prose-sm max-w-none dark:prose-invert">
                          <ReactMarkdown>{message.content}</ReactMarkdown>
                        </div>
                      </>
                    )}
                  </div>

                  {message.role === 'user' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center">
                      <User className="w-5 h-5 text-white" />
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="px-4 py-2 bg-red-50 border-t border-red-100 flex items-center gap-2 text-red-700">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {/* Input */}
        <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200">
          <div className="flex gap-2">
            <Input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Fragen Sie nach Gesetzen, Insolvenzen, Verträgen..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="px-4"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </Button>
          </div>
          <p className="mt-2 text-xs text-gray-500 text-center">
            DealGuard AI nutzt echte Daten aus RIS (Rechtsinformationssystem) und
            Ediktsdatei. Keine Halluzinationen.
          </p>
        </form>
      </Card>
    </div>
  );
}
