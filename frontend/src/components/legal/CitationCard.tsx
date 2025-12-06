'use client';

import { useState } from 'react';
import { Citation } from '@/lib/api/client';

interface CitationCardProps {
  citation: Citation;
  isExpanded?: boolean;
}

export function CitationCard({ citation, isExpanded = false }: CitationCardProps) {
  const [expanded, setExpanded] = useState(isExpanded);

  return (
    <div className="border border-gray-200 rounded-lg bg-gray-50 overflow-hidden">
      {/* Header - always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center justify-between text-left hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-medium bg-blue-100 text-blue-700 rounded">
            {citation.number}
          </span>
          <span className="text-sm font-medium text-gray-900 truncate max-w-[200px]">
            {citation.contract_filename}
          </span>
          {citation.page && (
            <span className="text-xs text-gray-500">
              Seite {citation.page}
            </span>
          )}
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-3 pb-3 border-t border-gray-200">
          <blockquote className="mt-2 text-sm text-gray-700 italic border-l-2 border-blue-300 pl-3">
            "{citation.clause_text}"
          </blockquote>
          {citation.paragraph && (
            <p className="mt-1 text-xs text-gray-500">
              {citation.paragraph}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

interface CitationListProps {
  citations: Citation[];
}

export function CitationList({ citations }: CitationListProps) {
  if (citations.length === 0) return null;

  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
        Quellen ({citations.length})
      </p>
      {citations.map((citation) => (
        <CitationCard key={citation.number} citation={citation} />
      ))}
    </div>
  );
}

interface InlineCitationProps {
  number: number;
  citation: Citation;
}

export function InlineCitation({ number, citation }: InlineCitationProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <span className="relative inline-block">
      <button
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={() => setShowTooltip(!showTooltip)}
        className="inline-flex items-center justify-center w-4 h-4 text-[10px] font-medium bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors cursor-help"
      >
        {number}
      </button>

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg">
          <p className="font-medium">{citation.contract_filename}</p>
          {citation.page && <p className="text-gray-400">Seite {citation.page}</p>}
          <p className="mt-1 italic text-gray-300 line-clamp-3">
            "{citation.clause_text}"
          </p>
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
        </div>
      )}
    </span>
  );
}
