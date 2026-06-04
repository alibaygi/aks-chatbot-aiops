import type { Conversation, Message, TokenResponse, User } from '@/types';

const BASE = '/api/v1';

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const t = getToken();
  return {
    'Content-Type': 'application/json',
    ...(t ? { Authorization: `Bearer ${t}` } : {}),
    ...extra,
  };
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export async function apiRegister(email: string, password: string): Promise<User> {
  const res = await fetch(`${BASE}/auth/register`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ email, password }),
  });
  return handleResponse<User>(res);
}

export async function apiLogin(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ email, password }),
  });
  return handleResponse<TokenResponse>(res);
}

export async function apiGetMe(): Promise<User> {
  const res = await fetch(`${BASE}/auth/me`, { headers: authHeaders() });
  return handleResponse<User>(res);
}

// ─── Conversations ────────────────────────────────────────────────────────────

export async function apiListConversations(): Promise<Conversation[]> {
  const res = await fetch(`${BASE}/conversations`, { headers: authHeaders() });
  return handleResponse<Conversation[]>(res);
}

export async function apiCreateConversation(): Promise<Conversation> {
  const res = await fetch(`${BASE}/conversations`, {
    method: 'POST',
    headers: authHeaders(),
  });
  return handleResponse<Conversation>(res);
}

export async function apiDeleteConversation(id: string): Promise<void> {
  await fetch(`${BASE}/conversations/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
}

export async function apiGetMessages(id: string): Promise<Message[]> {
  const res = await fetch(`${BASE}/conversations/${id}/messages`, {
    headers: authHeaders(),
  });
  return handleResponse<Message[]>(res);
}

// ─── Streaming ────────────────────────────────────────────────────────────────

export async function apiSendMessage(
  conversationId: string,
  content: string,
  onChunk: (chunk: string) => void,
  onTitle: (title: string) => void,
  onDone: () => void,
  onError: (detail: string) => void,
): Promise<void> {
  const token = getToken();
  const res = await fetch(`${BASE}/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ content }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buf = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buf += decoder.decode(value, { stream: true });

    // SSE events are separated by double newline
    const parts = buf.split('\n\n');
    buf = parts.pop() ?? '';

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith('data: ')) continue;
      const jsonStr = line.slice(6);
      try {
        const event = JSON.parse(jsonStr) as { type: string; content?: string; title?: string; detail?: string };
        if (event.type === 'chunk' && event.content) onChunk(event.content);
        else if (event.type === 'title' && event.title) onTitle(event.title);
        else if (event.type === 'done') onDone();
        else if (event.type === 'error' && event.detail) onError(event.detail);
      } catch {
        // malformed JSON, skip
      }
    }
  }
}
