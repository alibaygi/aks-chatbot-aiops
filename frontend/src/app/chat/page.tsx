'use client';

import { BotMessageSquare, MessageSquarePlus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import toast from 'react-hot-toast';
import { useConversations } from '@/context/ConversationsContext';
import { apiCreateConversation } from '@/lib/api';

export default function ChatIndexPage() {
  const { prependConversation } = useConversations();
  const router = useRouter();
  const [creating, setCreating] = useState(false);

  const handleNewChat = async () => {
    setCreating(true);
    try {
      const conv = await apiCreateConversation();
      prependConversation(conv);
      router.push(`/chat/${conv.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create conversation');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="h-full flex flex-col items-center justify-center gap-6 px-4">
      <div className="flex flex-col items-center gap-3 text-center">
        <BotMessageSquare
          className="w-14 h-14 mb-2"
          style={{ color: 'var(--accent)' }}
        />
        <h1 className="text-2xl font-semibold">How can I help you today?</h1>
        <p className="text-sm max-w-xs" style={{ color: 'var(--muted)' }}>
          I can answer questions, search the web, and remember things about you across conversations.
        </p>
      </div>

      <button
        onClick={handleNewChat}
        disabled={creating}
        className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-opacity cursor-pointer"
        style={{
          background: 'var(--accent)',
          color: '#fff',
          opacity: creating ? 0.7 : 1,
        }}
      >
        <MessageSquarePlus size={16} />
        {creating ? 'Creating…' : 'Start a new chat'}
      </button>
    </div>
  );
}
