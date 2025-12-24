'use client';

import { LegalMessage } from '@/lib/api/client';
import { CitationList } from './CitationCard';

interface ChatMessageProps {
  message: LegalMessage;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-white border border-gray-200 text-gray-900'
        }`}
      >
        {/* Message content */}
        <div className={`text-sm whitespace-pre-wrap ${isUser ? '' : 'prose prose-sm max-w-none'}`}>
          {message.content}
        </div>

        {/* Assistant-specific elements */}
        {!isUser && (
          <>
            {/* Confidence indicator */}
            {message.confidence !== null && (
              <div className="mt-2 flex items-center gap-2">
                <ConfidenceBadge confidence={message.confidence} />
                {message.requires_lawyer && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-800 rounded-full">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    Anwalt empfohlen
                  </span>
                )}
              </div>
            )}

            {/* Citations */}
            {message.citations && message.citations.length > 0 && (
              <CitationList citations={message.citations} />
            )}
          </>
        )}

        {/* Timestamp */}
        <p className={`mt-1 text-xs ${isUser ? 'text-blue-200' : 'text-gray-400'}`}>
          {formatTime(message.created_at)}
        </p>
      </div>
    </div>
  );
}

interface ConfidenceBadgeProps {
  confidence: number;
}

function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const percent = Math.round(confidence * 100);

  let colorClass = 'bg-green-100 text-green-800';
  let label = 'Hohe Sicherheit';

  if (confidence < 0.5) {
    colorClass = 'bg-red-100 text-red-800';
    label = 'Geringe Sicherheit';
  } else if (confidence < 0.7) {
    colorClass = 'bg-amber-100 text-amber-800';
    label = 'Mittlere Sicherheit';
  } else if (confidence < 0.9) {
    colorClass = 'bg-blue-100 text-blue-800';
    label = 'Gute Sicherheit';
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${colorClass}`}>
      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
      {label} ({percent}%)
    </span>
  );
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('de-AT', {
    hour: '2-digit',
    minute: '2-digit',
  });
}
