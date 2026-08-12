/**
 * API service functions for all backend endpoints.
 */
import apiClient from '@/lib/api-client';
import type {
  LoginResponse,
  User,
  Conversation,
  Message,
  Memory,
  MemorySearchResult,
  MemorySearchResponse,
  MemoryStats,
  PaginatedResponse,
  ChatResponse,
} from '@/types';

// ── Auth ──────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<LoginResponse>('/auth/login', { email, password }).then((r) => r.data),

  register: (username: string, email: string, password: string, full_name?: string) =>
    apiClient.post<User>('/auth/register', { username, email, password, full_name }).then((r) => r.data),

  me: () => apiClient.get<User>('/auth/me').then((r) => r.data),

  logout: () => apiClient.post('/auth/logout').then((r) => r.data),

  refreshToken: (refresh_token: string) =>
    apiClient.post<{ access_token: string }>('/auth/refresh', { refresh_token }).then((r) => r.data),
};

// ── Conversations ─────────────────────────────────────────────
export const conversationApi = {
  list: (page = 1, page_size = 20) =>
    apiClient.get<PaginatedResponse<Conversation>>('/chat/conversations', { params: { page, page_size } }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Conversation>(`/chat/conversations/${id}`).then((r) => r.data),

  create: (title?: string) =>
    apiClient.post<Conversation>('/chat/conversations', { title }).then((r) => r.data),

  update: (id: string, data: Partial<Conversation>) =>
    apiClient.put<Conversation>(`/chat/conversations/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/chat/conversations/${id}`).then((r) => r.data),

  messages: (id: string) =>
    apiClient.get<Message[]>(`/chat/conversations/${id}/messages`).then((r) => r.data),

  summarize: (id: string) =>
    apiClient.post<{ summary: string }>(`/chat/conversations/${id}/summarize`).then((r) => r.data),

  export: (id: string) =>
    apiClient.get<Blob>(`/chat/conversations/${id}/export`, { responseType: 'blob' }).then((r) => r.data),
};

// ── Chat (non-streaming) ─────────────────────────────────────
export const chatApi = {
  send: (message: string, conversation_id?: string, use_memory = true) =>
    apiClient
      .post<ChatResponse>('/chat/message', { message, conversation_id, use_memory, stream: false })
      .then((r) => r.data),
};

// ── Memory ────────────────────────────────────────────────────
export const memoryApi = {
  stats: () =>
    apiClient.get<MemoryStats>('/memories/stats').then((r) => r.data),

  search: (query: string, limit = 5) =>
    apiClient.post<MemorySearchResponse>('/memories/search', { query, top_k: limit }).then((r) => r.data),

  list: (
    paramsOrPage?:
      | number
      | {
          page?: number;
          page_size?: number;
          memory_type?: string;
          is_active?: boolean;
          search_query?: string;
          status?: string;
          sort_by?: string;
        },
    page_size = 20,
    memory_type?: string
  ) => {
    const params =
      typeof paramsOrPage === 'number'
        ? { page: paramsOrPage, page_size, memory_type }
        : paramsOrPage;
    return apiClient
      .get<PaginatedResponse<Memory>>('/memories', { params })
      .then((r) => r.data);
  },

  get: (id: string) =>
    apiClient.get<Memory>(`/memories/${id}`).then((r) => r.data),

  update: (id: string, data: Partial<Memory>) =>
    apiClient.put<Memory>(`/memories/${id}`, data).then((r) => r.data),

  archive: (id: string) =>
    apiClient.post<Memory>(`/memories/${id}/archive`).then((r) => r.data),

  restore: (id: string) =>
    apiClient.post<Memory>(`/memories/${id}/restore`).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/memories/${id}`).then((r) => r.data),
};

// ── Debugger & Explainability ────────────────────────────────
export const debugApi = {
  getLatest: () =>
    apiClient.get('/debug/latest').then((r) => r.data),

  getForConversation: (id: string) =>
    apiClient.get(`/debug/conversation/${id}`).then((r) => r.data),

  getPromptTrace: (id: string) =>
    apiClient.get(`/debug/prompt/${id}`).then((r) => r.data),
};

// ── Streaming chat ────────────────────────────────────────────
export async function streamChat(
  message: string,
  conversation_id: string | undefined,
  onChunk: (text: string) => void,
  onMemories: (memories: MemorySearchResult[]) => void,
  onDone: (finish_reason?: string) => void,
  onError: (err: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = localStorage.getItem('access_token');
  const res = await fetch('/api/v1/chat/send', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, conversation_id, use_memory: true, stream: true }),
    signal,
  });

  if (!res.ok) {
    const err = await res.text();
    onError(err);
    return;
  }

  const reader = res.body?.getReader();
  const decoder = new TextDecoder();
  if (!reader) return;

  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const raw = line.slice(6).trim();
      if (!raw || raw === '[DONE]') continue;
      try {
        const chunk = JSON.parse(raw);
        if (chunk.type === 'chunk' && chunk.content) onChunk(chunk.content);
        else if (chunk.type === 'memory_context' && chunk.memories) onMemories(chunk.memories);
        else if (chunk.type === 'done') onDone(chunk.finish_reason);
        else if (chunk.type === 'error') onError(chunk.error ?? 'Unknown error');
      } catch {
        // skip malformed
      }
    }
  }
}
