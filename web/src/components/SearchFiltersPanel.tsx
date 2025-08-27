import React from 'react'
import { X } from 'lucide-react'
import { SearchFilters } from '../types'

interface SearchFiltersPanelProps {
  filters: SearchFilters
  onFiltersChange: (filters: SearchFilters) => void
  projects: string[]
}

export default function SearchFiltersPanel({ 
  filters, 
  onFiltersChange, 
  projects 
}: SearchFiltersPanelProps) {
  
  const updateFilter = (key: keyof SearchFilters, value: any) => {
    onFiltersChange({
      ...filters,
      [key]: value || undefined
    })
  }

  const clearFilters = () => {
    onFiltersChange({})
  }

  const hasActiveFilters = Object.values(filters).some(value => value !== undefined && value !== '')

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-900">Search Filters</h3>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center"
          >
            <X className="h-4 w-4 mr-1" />
            Clear all
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Project Filter */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Project
          </label>
          <select
            value={filters.project || ''}
            onChange={(e) => updateFilter('project', e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All projects</option>
            {projects.map((project) => {
              const displayName = project
                .replace(/^-home-\w+-/, '')
                .replace(/-/g, ' ')
                .replace(/\b\w/g, l => l.toUpperCase())
              
              return (
                <option key={project} value={project}>
                  {displayName}
                </option>
              )
            })}
          </select>
        </div>

        {/* Role Filter */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Role
          </label>
          <select
            value={filters.role || ''}
            onChange={(e) => updateFilter('role', e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All roles</option>
            <option value="user">User</option>
            <option value="assistant">Assistant</option>
            <option value="system">System</option>
          </select>
        </div>

        {/* Date After */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            After Date
          </label>
          <input
            type="date"
            value={filters.dateAfter || ''}
            onChange={(e) => updateFilter('dateAfter', e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* Date Before */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Before Date
          </label>
          <input
            type="date"
            value={filters.dateBefore || ''}
            onChange={(e) => updateFilter('dateBefore', e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      {/* Advanced Options */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Similarity Threshold */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Similarity Threshold: {((filters.threshold || 0.7) * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={filters.threshold || 0.7}
              onChange={(e) => updateFilter('threshold', parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>More results</span>
              <span>More precise</span>
            </div>
          </div>

          {/* Result Limit */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Max Results
            </label>
            <select
              value={filters.limit || 20}
              onChange={(e) => updateFilter('limit', parseInt(e.target.value))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value={10}>10 results</option>
              <option value={20}>20 results</option>
              <option value={50}>50 results</option>
              <option value={100}>100 results</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}