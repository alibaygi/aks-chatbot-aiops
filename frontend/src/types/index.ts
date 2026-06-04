export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export type SSEEvent =
  | { type: 'chunk'; content: string }
  | { type: 'title'; title: string }
  | { type: 'error'; detail: string }
  | { type: 'done' };
