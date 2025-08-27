import { useState } from "react"
import { Search, Filter } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { searchConversations, getProjects } from '../api/search'
import { SearchResult, SearchFilters } from '../types'
import ResultCard from './ResultCard'
import SearchFiltersPanel from './SearchFiltersPanel'

interface SearchInterfaceProps {
  onResultClick: (result: SearchResult) => void
}

export default function SearchInterface({ onResultClick }: SearchInterfaceProps) {
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState<SearchFilters>({})
  const [showFilters, setShowFilters] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  // Get available projects for filter dropdown
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  })

  // Search query
  const { data: searchResults, isLoading, error } = useQuery({
    queryKey: ['search', query, filters],
    queryFn: () => searchConversations(query, filters),
    enabled: hasSearched && query.trim().length > 0,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      setHasSearched(true)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch(e as any)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Search Bar */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="relative flex items-center">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Search your conversations... (e.g., 'database performance', 'React components', 'error handling')"
            className="block w-full pl-10 pr-20 py-3 border border-gray-300 rounded-lg text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          <div className="absolute inset-y-0 right-0 flex items-center">
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className="p-2 mr-2 text-gray-400 hover:text-gray-600 rounded-md"
            >
              <Filter className="h-5 w-5" />
            </button>
            <button
              type="submit"
              disabled={!query.trim()}
              className="mr-2 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Search
            </button>
          </div>
        </div>
      </form>

      {/* Filters Panel */}
      {showFilters && (
        <SearchFiltersPanel
          filters={filters}
          onFiltersChange={setFilters}
          projects={projects || []}
        />
      )}

      {/* Search Results */}
      {hasSearched && (
        <div className="mt-6">
          {isLoading && (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <p className="mt-2 text-gray-600">Searching conversations...</p>
            </div>
          )}

          {error && (
            <div className="text-center py-8">
              <p className="text-red-600">Error searching conversations. Please try again.</p>
            </div>
          )}

          {searchResults && (
            <div>
              <div className="mb-4 text-sm text-gray-600">
                Found {searchResults.total} results for "{searchResults.query}"
              </div>

              {searchResults.results.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>No conversations found matching your search.</p>
                  <p className="text-sm mt-2">Try different keywords or adjust your filters.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {searchResults.results.map((result) => (
                    <ResultCard
                      key={result.id}
                      result={result}
                      onClick={() => onResultClick(result)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Initial State */}
      {!hasSearched && (
        <div className="text-center py-12">
          <Search className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Start searching your conversations
          </h3>
          <p className="text-gray-500 max-w-md mx-auto">
            Enter keywords or phrases to find relevant conversations from your Claude Code sessions.
            The search uses semantic similarity to find related content even if the exact words don't match.
          </p>
        </div>
      )}
    </div>
  )
}