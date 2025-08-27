import { useState, useEffect } from "react"
import { ArrowLeft, User, Bot, Settings, FileText } from 'lucide-react'

interface Message {
  id: string
  role: string
  content: string
  timestamp: string
  tool_uses?: any
}

interface ConversationViewProps {
  sessionId: string
  onBack: () => void
}

export default function ConversationView({ sessionId, onBack }: ConversationViewProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [conversationInfo, setConversationInfo] = useState<any>(null)

  useEffect(() => {
    fetchConversation()
  }, [sessionId])

  const fetchConversation = async () => {
    try {
      setLoading(true)
      
      // Find the conversation by session_id
      const conversationsResponse = await fetch('/api/conversations?limit=100')
      const conversationsData = await conversationsResponse.json()
      
      const conversation = conversationsData.conversations.find((c: any) => c.session_id === sessionId)
      if (!conversation) {
        console.error('Conversation not found')
        return
      }
      
      setConversationInfo(conversation)
      
      // Get all messages for this conversation
      const messagesResponse = await fetch(`/api/conversations/${conversation.id}/messages?limit=1000`)
      const messagesData = await messagesResponse.json()
      
      if (messagesData.messages) {
        setMessages(messagesData.messages)
      }
    } catch (error) {
      console.error('Error fetching conversation:', error)
    } finally {
      setLoading(false)
    }
  }

  const getMessageIcon = (role: string) => {
    switch (role) {
      case 'user':
        return <User className="h-5 w-5" />
      case 'assistant':
        return <Bot className="h-5 w-5" />
      case 'tool':
        return <Settings className="h-5 w-5" />
      default:
        return <FileText className="h-5 w-5" />
    }
  }

  const getMessageStyle = (role: string) => {
    switch (role) {
      case 'user':
        return 'bg-blue-50 border-blue-200 text-blue-900'
      case 'assistant':
        return 'bg-green-50 border-green-200 text-green-900'
      case 'tool':
        return 'bg-purple-50 border-purple-200 text-purple-900'
      default:
        return 'bg-gray-50 border-gray-200 text-gray-900'
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading conversation...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={onBack}
          className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Search</span>
        </button>
        
        {conversationInfo && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Conversation Details</h1>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600">
              <div>
                <strong>Project:</strong> {conversationInfo.project_name}
              </div>
              <div>
                <strong>Started:</strong> {new Date(conversationInfo.started_at).toLocaleString()}
              </div>
              <div>
                <strong>Messages:</strong> {messages.length}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`p-4 rounded-lg border ${getMessageStyle(message.role)}`}
          >
            {/* Message Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                {getMessageIcon(message.role)}
                <span className="font-medium capitalize">{message.role}</span>
                {message.role === 'assistant' && (
                  <span className="text-xs bg-white bg-opacity-50 px-2 py-1 rounded">
                    Claude
                  </span>
                )}
              </div>
              <div className="text-xs opacity-75">
                {new Date(message.timestamp).toLocaleString()}
              </div>
            </div>

            {/* Message Content */}
            <div className="prose prose-sm max-w-none">
              <pre className="whitespace-pre-wrap text-sm font-sans">
                {message.content}
              </pre>
            </div>

            {/* Tool Uses (if any) */}
            {message.tool_uses && (
              <div className="mt-3 p-3 bg-white bg-opacity-50 rounded border text-xs">
                <strong>Tool Usage:</strong>
                <pre className="mt-1 whitespace-pre-wrap">
                  {typeof message.tool_uses === 'string' 
                    ? message.tool_uses 
                    : JSON.stringify(message.tool_uses, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>

      {messages.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No messages found in this conversation.</p>
        </div>
      )}
    </div>
  )
}