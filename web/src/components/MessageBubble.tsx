import React, { useState } from 'react'
import { User, Bot, Settings, ChevronDown, ChevronRight, Code, Terminal, Wrench } from 'lucide-react'
import { Message } from '../types'

interface MessageBubbleProps {
  message: Message
  isHighlighted?: boolean
  isMatched?: boolean
  searchQuery?: string
}

export default function MessageBubble({ 
  message, 
  isHighlighted = false, 
  isMatched = false,
  searchQuery 
}: MessageBubbleProps) {
  const [showToolUses, setShowToolUses] = useState(false)

  // Get the effective role - now that data is properly classified, just use the stored role
  const getEffectiveRole = (message: Message) => {
    return message.role
  }

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'user':
        return <User className="h-4 w-4" />
      case 'assistant':
        return <Bot className="h-4 w-4" />
      case 'system':
        return <Settings className="h-4 w-4" />
      case 'tool':
        return <Wrench className="h-4 w-4" />
      default:
        return <Bot className="h-4 w-4" />
    }
  }

  const getRoleStyles = (role: string) => {
    switch (role) {
      case 'user':
        return 'bg-blue-50 border-blue-200'
      case 'assistant':
        return 'bg-green-50 border-green-200'
      case 'system':
        return 'bg-gray-50 border-gray-200'
      case 'tool':
        return 'bg-amber-50 border-amber-200'
      default:
        return 'bg-gray-50 border-gray-200'
    }
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'user':
        return 'text-blue-700'
      case 'assistant':
        return 'text-green-700'
      case 'system':
        return 'text-gray-700'
      case 'tool':
        return 'text-amber-700'
      default:
        return 'text-gray-700'
    }
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  // Highlight search terms in content
  const highlightContent = (content: string, query?: string) => {
    if (!query || !isMatched) return content

    // Simple highlighting - in a production app you'd want more sophisticated matching
    const words = query.toLowerCase().split(' ').filter(w => w.length > 2)
    let highlightedContent = content

    words.forEach(word => {
      const regex = new RegExp(`(${word})`, 'gi')
      highlightedContent = highlightedContent.replace(
        regex, 
        '<mark class="bg-yellow-200 px-1 rounded">$1</mark>'
      )
    })

    return highlightedContent
  }

  // Check if content looks like code
  const isCodeContent = (content: string) => {
    return content.includes('```') || 
           content.includes('function ') ||
           content.includes('const ') ||
           content.includes('import ') ||
           content.includes('export ') ||
           content.match(/^\s*[\{\[\(]/) ||
           content.includes('</') ||
           content.includes('/>')
  }

  const hasToolUses = message.tool_uses && Object.keys(message.tool_uses).length > 0
  const effectiveRole = getEffectiveRole(message)

  return (
    <div 
      className={`border rounded-lg p-4 transition-all duration-200 ${
        getRoleStyles(effectiveRole)
      } ${
        isHighlighted ? 'ring-2 ring-primary-500 shadow-lg' : ''
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div className={`flex items-center space-x-1 ${getRoleColor(effectiveRole)}`}>
            {getRoleIcon(effectiveRole)}
            <span className="text-sm font-medium capitalize">{effectiveRole}</span>
          </div>
          {isMatched && (
            <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full font-medium">
              Search Match
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500">
          {message.timestamp ? formatTimestamp(message.timestamp) : 'No timestamp'}
        </div>
      </div>

      {/* Content */}
      <div className="prose prose-sm max-w-none">
        {isCodeContent(message.content) ? (
          <div className="bg-gray-900 text-gray-100 p-4 rounded-md overflow-x-auto">
            <pre className="text-sm">
              <code 
                dangerouslySetInnerHTML={{ 
                  __html: highlightContent(message.content, searchQuery) 
                }} 
              />
            </pre>
          </div>
        ) : (
          <div 
            className="text-gray-900 whitespace-pre-wrap leading-relaxed"
            dangerouslySetInnerHTML={{ 
              __html: highlightContent(message.content, searchQuery) 
            }}
          />
        )}
      </div>

      {/* Tool Uses */}
      {hasToolUses && (
        <div className="mt-4 pt-3 border-t border-gray-200">
          <button
            onClick={() => setShowToolUses(!showToolUses)}
            className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-900"
          >
            {showToolUses ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <Terminal className="h-4 w-4" />
            <span>Tool Uses</span>
          </button>
          
          {showToolUses && (
            <div className="mt-2 bg-gray-100 rounded p-3">
              <pre className="text-xs text-gray-700 overflow-x-auto">
                {JSON.stringify(message.tool_uses, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}