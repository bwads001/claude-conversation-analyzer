# Implementation Notes

## Context
This document captures key technical decisions and implementation details from the initial planning session. These notes supplement the README with specific architectural choices and rationale.

## Key Architectural Decisions

### Why PostgreSQL + pgvector (not SQLite or pure vector DB)
- **Hybrid Queries**: Need both SQL (timeline, project filtering) AND semantic search
- **Unified System**: One database for structured and vector data
- **Production Ready**: PostgreSQL is battle-tested, pgvector is mature
- **Query Example**: 
```sql
-- Find similar work in specific project and timeframe
SELECT * FROM messages m
JOIN conversations c ON m.conv_id = c.id
WHERE c.project = 'my-project-main-feature-branch'
  AND c.timestamp > '2025-08-01'
  AND m.embedding <=> embed('performance optimization') < 0.5
ORDER BY m.embedding <=> embed('performance optimization');
```

### Embedding Model Choice
- **Model**: `nomic-embed-text` (768 dimensions)
- **Why**: Good balance of quality/speed, works well on RTX 4070 Ti
- **Alternative**: `mxbai-embed-large` (1024 dims) for better quality if needed
- **Local via Ollama**: Privacy, no API costs, fast with GPU acceleration

### Project Classification Strategy
- **Use Existing Structure**: Claude already organizes by project directory
- **No Complex Categorization**: Project path IS the category
- **Pattern**: `/home/{user}/.claude/projects/{encoded-project-path}/`
- **Example**: `-home-user-myproject-main-feature-branch`

## Implementation Priority Order

### Phase 1: Core Pipeline (Start Here)
1. **JSONL Parser** (`src/parser.py`)
   - Extract conversation metadata (timestamp, project, git branch)
   - Parse messages with role (user/assistant)
   - Extract tool uses (file operations, bash commands, etc.)
   - Handle the "no timestamp" issue for first message

2. **Embedding Pipeline** (`src/embeddings.py`)
   - Interface with Ollama API (http://localhost:11434)
   - Batch processing for efficiency
   - Store both content and embedding vector
   - Consider chunking for long messages

3. **Database Layer** (`src/database.py`)
   - Schema initialization with pgvector extension
   - Bulk insert capabilities
   - Connection pooling for performance
   - Transaction handling for consistency

4. **Basic Search** (`scripts/search_cli.py`)
   - Simple semantic similarity search
   - Display results with context
   - Show relevance scores

### Phase 2: Enhanced Capabilities
- Timeline generation from conversations
- Work journal automation
- Cross-session correlation
- Technical pattern extraction

## Database Schema Details

```sql
-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Main conversation table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_name TEXT NOT NULL,
    project_path TEXT NOT NULL,  -- Full encoded path
    session_id TEXT NOT NULL,    -- Original JSONL filename
    git_branch TEXT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    message_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Messages with embeddings
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT,
    embedding vector(768),  -- nomic-embed-text dimensions
    timestamp TIMESTAMP,
    tool_uses JSONB,       -- Structured tool call data
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Extracted technical events for analysis
CREATE TABLE technical_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,  -- 'file_created', 'error_resolved', 'test_run', etc.
    file_path TEXT,
    details JSONB,
    timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_messages_embedding ON messages 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);  -- Adjust based on data size

CREATE INDEX idx_conversations_project ON conversations(project_name, started_at DESC);
CREATE INDEX idx_messages_timestamp ON messages(conversation_id, timestamp);
CREATE INDEX idx_technical_events_type ON technical_events(event_type, timestamp DESC);
```

## JSONL Parsing Notes

### Message Structure
```python
{
    "uuid": "msg-uuid",
    "type": "user|assistant",
    "timestamp": "2025-08-26T13:52:51.800Z",  # Sometimes missing on first message
    "message": {
        "role": "user|assistant",
        "content": [...]  # Can be string or array of content blocks
    },
    "toolUseResult": {...},  # Optional, contains file operations
    "cwd": "/path/to/working/dir",
    "gitBranch": "feature/branch-name"
}
```

### Edge Cases to Handle
1. **Missing Timestamps**: First message often lacks timestamp, use next message or file mtime
2. **Content Format**: Can be string or array of content blocks
3. **Tool Results**: Parse for file operations, track what was created/modified
4. **Large Messages**: Consider chunking for embedding (but maintain context)
5. **System Messages**: Filter or mark appropriately

## Embedding Generation Strategy

```python
# Batch processing for efficiency
def generate_embeddings(texts: List[str], model="nomic-embed-text") -> List[List[float]]:
    # Ollama can handle batches efficiently
    # Consider rate limiting if needed (unlikely for local)
    
    # For long texts, options:
    # 1. Truncate to model max length
    # 2. Chunk and average embeddings
    # 3. Use first N tokens (often most relevant)
    
    # Return normalized vectors for cosine similarity
```

## Search Implementation Notes

### Similarity Threshold
- Cosine similarity < 0.3 = very similar
- Cosine similarity < 0.5 = relevant  
- Cosine similarity < 0.7 = somewhat related
- Adjust based on user feedback

### Result Ranking
1. Primary: Vector similarity score
2. Secondary: Recency (timestamp)
3. Tertiary: Project relevance (if project filter applied)

### Query Enhancement
- Consider expanding queries with synonyms
- For code searches, include error message patterns
- For timeline queries, bias toward temporal ordering

## Performance Considerations

### Expected Scale
- Typical user: 100-1000 conversation files
- Average conversation: 50-200 messages
- Total messages: ~50,000-200,000
- Database size: ~1-5GB with embeddings

### Optimization Points
1. **Batch Ingestion**: Process multiple files in single transaction
2. **Embedding Cache**: Store embeddings to avoid regeneration
3. **Index Tuning**: Adjust IVFFlat lists parameter based on data size
4. **Connection Pooling**: Reuse database connections
5. **Async Processing**: Use asyncpg for better concurrency

## Testing Strategy

### Test Data
- Use sanitized example conversations in `setup/test_data/`
- Create minimal JSONL files for edge cases
- Test with different project structures

### Key Test Cases
1. Parse conversation with missing timestamps
2. Handle very long messages (>10k chars)
3. Search with no results
4. Search with hundreds of results
5. Project filtering accuracy
6. Timeline reconstruction across sessions

## Future Enhancements (Not Phase 1)

1. **Web UI**: FastAPI + HTMX for simple search interface
2. **Export Formats**: Markdown journals, CSV for analysis
3. **Pattern Detection**: Identify recurring problem/solution pairs
4. **Conversation Merging**: Combine related sessions automatically
5. **Smart Chunking**: Intelligent message splitting for better embeddings

---

*Last Updated: Initial planning session for claude-conversation-analyzer project*