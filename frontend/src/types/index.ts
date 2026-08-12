// API types matching backend schemas

export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  created_at: string;
  is_active: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Conversation {
  id: string;
  title: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  summary?: string;
  is_archived: boolean;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  tokens_used?: number;
  model?: string;
  metadata?: Record<string, unknown>;
}

export interface Memory {
  id: string;
  user_id: string;
  conversation_id?: string;
  content: string;
  summary?: string;
  memory_type?: string;
  importance_score: number;
  confidence?: number;
  tags: string[];
  version?: number;
  status?: string;
  is_active?: boolean;
  source_session_id?: string;
  created_at: string;
  updated_at: string;
  access_count: number;
  last_accessed?: string;
  expires_at?: string;
  chunk_index?: number;
}

export interface MemorySearchResult {
  memory: Memory;
  similarity_score: number;
}

export interface MemorySearchResponse {
  results: MemorySearchResult[];
  query: string;
  total: number;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  use_memory?: boolean;
  stream?: boolean;
}

export interface ChatResponse {
  message: Message;
  conversation_id: string;
  memories_used: number;
  context_tokens: number;
  model: string;
}

export interface StreamChunk {
  type: 'chunk' | 'done' | 'error' | 'memory_context';
  content?: string;
  memories?: MemorySearchResult[];
  error?: string;
  finish_reason?: string;
}

export interface MemoryStats {
  total_memories: number;
  active_memories: number;
  updated_memories?: number;
  summaries_count?: number;
  by_type: Record<string, number>;
  avg_importance: number;
  total_access_count: number;
  last_updated?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages?: number;
}

export type ImportanceLevel = 'high' | 'medium' | 'low';

export function getImportanceLevel(score: number): ImportanceLevel {
  if (score >= 0.7) return 'high';
  if (score >= 0.4) return 'medium';
  return 'low';
}
