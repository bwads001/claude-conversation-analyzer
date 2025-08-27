import { useState } from 'react'
import SearchInterface from './components/SearchInterface'
import ConversationModal from './components/ConversationModal'
import { SearchResult } from './types'

function App() {
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null)

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Claude Conversation Analyzer
          </h1>
          <p className="text-lg text-gray-600">
            Search your Claude Code conversation history with semantic similarity
          </p>
        </header>

        <SearchInterface onResultClick={setSelectedResult} />

        {selectedResult && (
          <ConversationModal
            result={selectedResult}
            onClose={() => setSelectedResult(null)}
          />
        )}
      </div>
    </div>
  )
}

export default App