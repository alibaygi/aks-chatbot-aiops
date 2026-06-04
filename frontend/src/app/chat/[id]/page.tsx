'use client';

import { use, useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';

import MessageBubble from '@/components/MessageBubble';
import MessageInput from '@/components/MessageInput';
import { useConversations } from '@/context/ConversationsContext';
import { apiGetMessages, apiSendMessage } from '@/lib/api';
import type { Message } from '@/types';

interface Props {
  params: Promise<{ id: string }>;
}

export default function ConversationPage({ params }: Props) {
  const { id } = use(params);
  const { updateTitle } = useConversations();
  const router = useRouter();

  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [inputValue, setInputValue] = useState('');
  const [streaming, setStreaming] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load message history when conversation id changes
  useEffect(() => {
    let cancelled = false;
    setLoadingHistory(true);
    setMessages([]);

    apiGetMessages(id)
      .then((msgs) => {
        if (!cancelled) setMessages(msgs);
      })
      .catch((err) => {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : 'Failed to load messages';
          if (msg.includes('404') || msg.toLowerCase().includes('not found')) {
            router.replace('/chat');
          } else {
            toast.error(msg);
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id, router]);

  const handleSend = useCallback(async () => {
    const content = inputValue.trim();
    if (!content || streaming) return;

    setInputValue('');
    setStreaming(true);

    // Optimistically add user message
    const userMsg: Message = { role: 'user', content };
    setMessages((prev) => [...prev, userMsg]);

    // Add placeholder assistant message that we'll fill in
    const assistantPlaceholder: Message = { role: 'assistant', content: '' };
    setMessages((prev) => [...prev, assistantPlaceholder]);

    let aborted = false;
    abortRef.current = () => {
      aborted = true;
    };

    try {
      await apiSendMessage(
        id,
        content,
        // onChunk
        (chunk) => {
          if (aborted) return;
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === 'assistant') {
              next[next.length - 1] = { ...last, content: last.content + chunk };
            }
            return next;
          });
        },
        // onTitle
        (title) => {
          if (!aborted) updateTitle(id, title);
        },
        // onDone
        () => {
          if (!aborted) setStreaming(false);
        },
        // onError
        (detail) => {
          if (!aborted) {
            toast.error(detail);
            setStreaming(false);
          }
        },
      );
    } catch (err) {
      if (!aborted) {
        toast.error(err instanceof Error ? err.message : 'Failed to send message');
        // Remove the empty placeholder on hard failure
        setMessages((prev) => {
          const next = [...prev];
          if (next[next.length - 1]?.role === 'assistant' && next[next.length - 1].content === '') {
            next.pop();
          }
          return next;
        });
        setStreaming(false);
      }
    } finally {
      abortRef.current = null;
    }
  }, [id, inputValue, streaming, updateTitle]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.();
    };
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
          {loadingHistory ? (
            <div className="flex justify-center pt-16">
              <div
                className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
                style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}
              />
            </div>
          ) : messages.length === 0 ? (
            <p className="text-center text-sm pt-16" style={{ color: 'var(--muted)' }}>
              Start the conversation below.
            </p>
          ) : (
            messages.map((msg, i) => {
              const isLastAssistant =
                i === messages.length - 1 && msg.role === 'assistant' && streaming;
              return (
                <MessageBubble
                  key={i}
                  message={msg}
                  streaming={isLastAssistant}
                />
              );
            })
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input area */}
      <div
        className="shrink-0 px-4 py-4"
        style={{ borderTop: '1px solid var(--border)' }}
      >
        <div className="max-w-3xl mx-auto">
          <MessageInput
            value={inputValue}
            onChange={setInputValue}
            onSubmit={handleSend}
            disabled={streaming || loadingHistory}
            placeholder={streaming ? 'AI is responding…' : 'Message AI Chat…'}
          />
          <p className="text-xs text-center mt-2.5" style={{ color: 'var(--muted)' }}>
            AI can make mistakes. Consider checking important information.
          </p>
        </div>
      </div>
    </div>
  );
}
