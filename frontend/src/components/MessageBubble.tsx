'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '@/types';

interface MessageBubbleProps {
  message: Message;
  /** If true, show blinking cursor at end (streaming in progress) */
  streaming?: boolean;
}

export default function MessageBubble({ message, streaming = false }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[75%] rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap"
          style={{ background: 'var(--surface)', color: 'var(--foreground)' }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 items-start">
      {/* AI avatar */}
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5"
        style={{ background: 'var(--accent)', color: '#fff' }}
      >
        AI
      </div>

      <div
        className={`flex-1 text-sm leading-relaxed prose-chat min-w-0 ${streaming ? 'cursor-blink' : ''}`}
        style={{ color: 'var(--foreground)' }}
      >
        {message.content ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        ) : streaming ? (
          <span style={{ color: 'var(--muted)' }}>Thinking…</span>
        ) : null}
      </div>
    </div>
  );
}
