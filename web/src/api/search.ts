import axios from 'axios'
import { SearchResponse, SearchFilters, Conversation } from '../types'

const api = axios.create({
  baseURL: '/api',
})

export const searchConversations = async (
  query: string,
  filters: SearchFilters = {}
): Promise<SearchResponse> => {
  const response = await api.get('/search', {
    params: {
      q: query,
      ...filters,
    }
  })
  return response.data
}

export const getConversation = async (conversationId: string): Promise<Conversation> => {
  const response = await api.get(`/conversations/${conversationId}`)
  return response.data
}

export const getConversationContext = async (
  conversationId: string,
  messageId: string,
  contextSize: number = 10
): Promise<Conversation> => {
  const response = await api.get(`/conversations/${conversationId}/context`, {
    params: {
      messageId,
      contextSize,
    }
  })
  return response.data
}

export const getProjects = async (): Promise<string[]> => {
  const response = await api.get('/projects')
  return response.data
}