import React, { useState } from 'react'
import { X, MessageSquare, Calendar, GitBranch, ExternalLink, ArrowLeft, ArrowRight } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getConversation, getConversationContext } from '../api/search'
import { SearchResult } from '../types'
import MessageBubble from './MessageBubble'

interface ConversationModalProps {
  result: SearchResult
  onClose: () => void
}

export default function ConversationModal({ result, onClose }: ConversationModalProps) {
  const [viewMode, setViewMode] = useState<'context' | 'full'>('context')
  const [contextSize, setContextSize] = useState(10)

  // Get conversation context around the matched message
  const { data: contextData, isLoading: contextLoading } = useQuery({
    queryKey: ['conversation-context', result.conversation_id, result.id, contextSize],
    queryFn: () => getConversationContext(result.conversation_id, result.id, contextSize),
    enabled: viewMode === 'context',
  })

  // Get full conversation
  const { data: fullData, isLoading: fullLoading } = useQuery({
    queryKey: ['conversation-full', result.conversation_id],
    queryFn: () => getConversation(result.conversation_id),
    enabled: viewMode === 'full',
  })

  const currentData = viewMode === 'context' ? contextData : fullData
  const isLoading = viewMode === 'context' ? contextLoading : fullLoading

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const projectDisplayName = result.project_name
    .replace(/^-home-\w+-/, '')
    .replace(/-/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())

  // Find the index of the matched message for highlighting
  const matchedMessageIndex = currentData?.messages.findIndex(msg => msg.id === result.id) ?? -1

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative flex h-full">
        <div className="ml-auto w-full max-w-4xl bg-white shadow-xl flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex-1">
              <div className="flex items-center space-x-4 mb-2">
                <h2 className="text-xl font-semibold text-gray-900">
                  {projectDisplayName}
                </h2>
                <div className="flex items-center space-x-4 text-sm text-gray-500">
                  {currentData?.started_at && (
                    <div className="flex items-center">
                      <Calendar className="h-4 w-4 mr-1" />
                      {formatTimestamp(currentData.started_at)}
                    </div>
                  )}
                  {currentData?.git_branch && (
                    <div className="flex items-center">
                      <GitBranch className="h-4 w-4 mr-1" />
                      {currentData.git_branch}
                    </div>
                  )}
                </div>
              </div>
              
              {/* View Mode Toggle */}
              <div className="flex items-center space-x-4">
                <div className="flex bg-gray-100 rounded-md p-1">
                  <button
                    onClick={() => setViewMode('context')}
                    className={`px-3 py-1 text-xs font-medium rounded ${
                      viewMode === 'context' 
                        ? 'bg-white text-gray-900 shadow-sm' 
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Context View
                  </button>
                  <button
                    onClick={() => setViewMode('full')}
                    className={`px-3 py-1 text-xs font-medium rounded ${
                      viewMode === 'full' 
                        ? 'bg-white text-gray-900 shadow-sm' 
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Full Conversation
                  </button>
                </div>
                
                {viewMode === 'context' && (
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-gray-600">Context:</span>
                    <select
                      value={contextSize}
                      onChange={(e) => setContextSize(parseInt(e.target.value))}
                      className="text-xs border border-gray-300 rounded px-2 py-1"
                    >
                      <option value={5}>±5 messages</option>
                      <option value={10}>±10 messages</option>
                      <option value={20}>±20 messages</option>
                    </select>
                  </div>
                )}
              </div>
            </div>
            
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-md"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-hidden">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-4"></div>
                  <p className="text-gray-600">Loading conversation...</p>
                </div>
              </div>
            ) : currentData ? (
              <div className="h-full overflow-y-auto p-6" style={{ maxHeight: 'calc(100vh - 200px)' }}>
                <div className="max-w-none">
                  {/* Messages */}
                  <div className="space-y-4">
                    {currentData.messages.map((message, index) => (
                      <MessageBubble
                        key={message.id}
                        message={message}
                        isHighlighted={message.id === result.id}
                        isMatched={message.id === result.id}
                        searchQuery={result.content}
                      />
                    ))}
                  </div>

                  {/* Footer Info */}
                  <div className="mt-8 pt-4 border-t border-gray-100 text-sm text-gray-500">
                    <div className="flex items-center justify-between">
                      <div>
                        {viewMode === 'context' && matchedMessageIndex >= 0 && (
                          <p>Showing {currentData.messages.length} messages around the match</p>
                        )}
                        {viewMode === 'full' && (
                          <p>Full conversation • {currentData.messages.length} messages</p>
                        )}
                      </div>
                      <div className="flex items-center space-x-2">
                        <span>Session: {currentData.session_id?.substring(0, 8)}...</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <p>Failed to load conversation</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}