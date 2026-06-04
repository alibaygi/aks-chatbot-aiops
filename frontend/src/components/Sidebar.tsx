'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  BotMessageSquare,
  LogOut,
  MessageSquarePlus,
  MoreHorizontal,
  Trash2,
  X,
} from 'lucide-react';
import toast from 'react-hot-toast';

import { useAuth } from '@/context/AuthContext';
import { useConversations } from '@/context/ConversationsContext';
import { apiCreateConversation, apiDeleteConversation } from '@/lib/api';

interface SidebarProps {
  mobileOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ mobileOpen, onClose }: SidebarProps) {
  const { user, logout } = useAuth();
  const { conversations, loading, removeConversation, prependConversation } = useConversations();
  const pathname = usePathname();
  const router = useRouter();
  const [creatingNew, setCreatingNew] = useState(false);
  const [activeMenu, setActiveMenu] = useState<string | null>(null);

  const handleNewChat = async () => {
    setCreatingNew(true);
    try {
      const conv = await apiCreateConversation();
      prependConversation(conv);
      router.push(`/chat/${conv.id}`);
      onClose();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create conversation');
    } finally {
      setCreatingNew(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setActiveMenu(null);
    try {
      await apiDeleteConversation(id);
      removeConversation(id);
      if (pathname === `/chat/${id}`) {
        router.push('/chat');
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete');
    }
  };

  const handleLogout = () => {
    logout();
    router.replace('/login');
  };

  const sidebarContent = (
    <div
      className="flex flex-col h-full"
      style={{ background: 'var(--sidebar-bg)', borderRight: '1px solid var(--border)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <div className="flex items-center gap-2">
          <BotMessageSquare className="w-5 h-5 shrink-0" style={{ color: 'var(--accent)' }} />
          <span className="font-semibold text-sm">AI Chat</span>
        </div>
        {/* Mobile close button */}
        <button
          className="lg:hidden p-1 rounded cursor-pointer"
          style={{ color: 'var(--muted)' }}
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </div>

      {/* New Chat button */}
      <div className="px-3 pb-2">
        <button
          onClick={handleNewChat}
          disabled={creatingNew}
          className="flex items-center gap-2 w-full rounded-lg px-3 py-2.5 text-sm transition-colors cursor-pointer"
          style={{
            color: 'var(--foreground)',
            background: 'transparent',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--surface)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
        >
          <MessageSquarePlus size={16} />
          <span>{creatingNew ? 'Creating…' : 'New chat'}</span>
        </button>
      </div>

      <div className="mx-3 mb-2" style={{ height: '1px', background: 'var(--border)' }} />

      {/* Conversations list */}
      <div className="flex-1 overflow-y-auto px-3 py-1 space-y-0.5">
        {loading ? (
          <div className="flex justify-center pt-8">
            <div
              className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: 'var(--muted)', borderTopColor: 'transparent' }}
            />
          </div>
        ) : conversations.length === 0 ? (
          <p className="text-xs text-center pt-6" style={{ color: 'var(--muted)' }}>
            No conversations yet
          </p>
        ) : (
          conversations.map((conv) => {
            const isActive = pathname === `/chat/${conv.id}`;
            return (
              <div key={conv.id} className="relative group">
                <Link
                  href={`/chat/${conv.id}`}
                  onClick={onClose}
                  className="flex items-center gap-2 w-full rounded-lg px-3 py-2 text-sm truncate transition-colors"
                  style={{
                    background: isActive ? 'var(--surface)' : 'transparent',
                    color: isActive ? 'var(--foreground)' : 'var(--muted)',
                    display: 'flex',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.background = '#1f1f1f';
                    e.currentTarget.style.color = 'var(--foreground)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'transparent';
                    if (!isActive) e.currentTarget.style.color = 'var(--muted)';
                  }}
                >
                  <span className="truncate flex-1">
                    {conv.title ?? 'New conversation'}
                  </span>
                </Link>

                {/* Three-dot menu */}
                <button
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                  style={{ color: 'var(--muted)' }}
                  onClick={(e) => {
                    e.preventDefault();
                    setActiveMenu(activeMenu === conv.id ? null : conv.id);
                  }}
                >
                  <MoreHorizontal size={14} />
                </button>

                {activeMenu === conv.id && (
                  <div
                    className="absolute right-0 top-full z-50 rounded-lg shadow-xl py-1 min-w-[130px]"
                    style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
                  >
                    <button
                      className="flex items-center gap-2 w-full px-3 py-2 text-sm transition-colors cursor-pointer text-red-400 hover:bg-red-500/10"
                      onClick={(e) => handleDelete(conv.id, e)}
                    >
                      <Trash2 size={14} />
                      Delete
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Footer – user info + logout */}
      <div className="px-3 pb-4 pt-2" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2 px-2 py-2">
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold shrink-0"
            style={{ background: 'var(--accent)', color: '#fff' }}
          >
            {user?.email?.[0]?.toUpperCase() ?? '?'}
          </div>
          <span className="text-xs truncate flex-1" style={{ color: 'var(--muted)' }}>
            {user?.email}
          </span>
          <button
            onClick={handleLogout}
            title="Log out"
            className="p-1.5 rounded transition-colors cursor-pointer shrink-0"
            style={{ color: 'var(--muted)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--foreground)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--muted)')}
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-64 shrink-0 flex-col h-full">{sidebarContent}</aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          {/* Backdrop */}
          <div
            className="absolute inset-0"
            style={{ background: 'rgba(0,0,0,0.6)' }}
            onClick={onClose}
          />
          {/* Drawer */}
          <aside className="relative z-50 w-64 flex flex-col h-full">{sidebarContent}</aside>
        </div>
      )}
    </>
  );
}
