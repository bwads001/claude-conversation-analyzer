import React from 'react'
import { MessageSquare, Calendar, GitBranch, User, Bot, Settings } from 'lucide-react'
import { SearchResult } from '../types'

interface ResultCardProps {
  result: SearchResult
  onClick: () => void
}

export default function ResultCard({ result, onClick }: ResultCardProps) {
  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'user':
        return <User className="h-4 w-4" />
      case 'assistant':
        return <Bot className="h-4 w-4" />
      case 'system':
        return <Settings className="h-4 w-4" />
      default:
        return <MessageSquare className="h-4 w-4" />
    }
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'user':
        return 'bg-blue-100 text-blue-800'
      case 'assistant':
        return 'bg-green-100 text-green-800'
      case 'system':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const similarityPercentage = Math.round((1 - result.similarity) * 100)

  // Clean project name for display
  const projectDisplayName = result.project_name
    .replace(/^-home-\w+-/, '')
    .replace(/-/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 cursor-pointer hover:shadow-md hover:border-primary-300 transition-all duration-200"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRoleColor(result.role)}`}>
            {getRoleIcon(result.role)}
            <span className="ml-1 capitalize">{result.role}</span>
          </span>
          <span className="text-sm text-primary-600 font-medium">
            {similarityPercentage}% match
          </span>
        </div>
        <div className="flex items-center text-sm text-gray-500">
          <Calendar className="h-4 w-4 mr-1" />
          {result.timestamp ? formatTimestamp(result.timestamp) : 'Unknown time'}
        </div>
      </div>

      {/* Content Preview */}
      <div className="mb-4">
        <p className="text-gray-900 leading-relaxed line-clamp-3">
          {result.content.length > 300 
            ? `${result.content.substring(0, 300)}...` 
            : result.content}
        </p>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-sm text-gray-500">
        <div className="flex items-center">
          <MessageSquare className="h-4 w-4 mr-1" />
          <span className="truncate max-w-xs">{projectDisplayName}</span>
        </div>
        {result.git_branch && (
          <div className="flex items-center ml-4">
            <GitBranch className="h-4 w-4 mr-1" />
            <span className="truncate max-w-xs">{result.git_branch}</span>
          </div>
        )}
      </div>
    </div>
  )
}