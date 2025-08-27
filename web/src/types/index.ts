export interface SearchResult {
  id: string
  content: string
  role: 'user' | 'assistant' | 'system'
  timestamp: string
  project_name: string
  git_branch?: string
  similarity: number
  conversation_id: string
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  query: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  tool_uses?: any
}

export interface Conversation {
  id: string
  project_name: string
  session_id: string
  started_at: string
  ended_at?: string
  git_branch?: string
  messages: Message[]
}

export interface SearchFilters {
  project?: string
  dateAfter?: string
  dateBefore?: string
  role?: 'user' | 'assistant' | 'system'
  threshold?: number
  limit?: number
}