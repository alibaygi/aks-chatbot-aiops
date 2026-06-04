'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Menu } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { ConversationsProvider } from '@/context/ConversationsContext';
import Sidebar from '@/components/Sidebar';

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
  }, [loading, user, router]);

  // Redirect to login if not authenticated
  if (!loading && !user) return null;

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div
          className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
          style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}
        />
      </div>
    );
  }

  return (
    <ConversationsProvider>
      <div className="flex h-full overflow-hidden" style={{ background: 'var(--background)' }}>
        <Sidebar
          mobileOpen={mobileSidebarOpen}
          onClose={() => setMobileSidebarOpen(false)}
        />

        {/* Main content area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Mobile top bar */}
          <div
            className="lg:hidden flex items-center gap-3 px-4 py-3 shrink-0"
            style={{ borderBottom: '1px solid var(--border)' }}
          >
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="p-1.5 rounded cursor-pointer"
              style={{ color: 'var(--muted)' }}
            >
              <Menu size={20} />
            </button>
            <span className="text-sm font-medium">AI Chat</span>
          </div>

          <div className="flex-1 overflow-hidden">{children}</div>
        </div>
      </div>
    </ConversationsProvider>
  );
}
