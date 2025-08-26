-- Database initialization script for Claude Conversation Analyzer
-- Creates schema with pgvector extension for semantic search

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Main conversation table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_name TEXT NOT NULL,
    project_path TEXT NOT NULL,
    session_id TEXT NOT NULL,
    git_branch TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    working_directory TEXT,
    message_count INTEGER DEFAULT 0,
    metadata JSONB,
    file_path TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages with embeddings for semantic search
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_uuid TEXT NOT NULL, -- Original UUID from JSONL
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768), -- nomic-embed-text dimensions (can be adjusted)
    timestamp TIMESTAMP WITH TIME ZONE,
    tool_uses JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Technical events extracted from tool uses
CREATE TABLE technical_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    file_path TEXT,
    details JSONB,
    timestamp TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance

-- Conversation indexes
CREATE INDEX idx_conversations_project ON conversations(project_name, started_at DESC);
CREATE UNIQUE INDEX idx_conversations_unique ON conversations(session_id, file_path);
CREATE INDEX idx_conversations_started_at ON conversations(started_at DESC);

-- Message indexes
CREATE INDEX idx_messages_conversation ON messages(conversation_id, timestamp);
CREATE INDEX idx_messages_role ON messages(role);
CREATE INDEX idx_messages_timestamp ON messages(timestamp DESC);
CREATE UNIQUE INDEX idx_messages_uuid ON messages(conversation_id, message_uuid);

-- Vector similarity search index (IVFFlat)
-- Note: This will be created after we have some data for better clustering
-- CREATE INDEX idx_messages_embedding ON messages 
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);

-- Technical events indexes
CREATE INDEX idx_technical_events_type ON technical_events(event_type, timestamp DESC);
CREATE INDEX idx_technical_events_conversation ON technical_events(conversation_id, timestamp);
CREATE INDEX idx_technical_events_file ON technical_events(file_path) WHERE file_path IS NOT NULL;

-- Full-text search indexes for hybrid search
CREATE INDEX idx_messages_content_fts ON messages USING gin(to_tsvector('english', content));

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_messages_updated_at BEFORE UPDATE ON messages  
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views for common queries

-- Conversation summary view
CREATE VIEW conversation_summary AS
SELECT 
    c.id,
    c.project_name,
    c.session_id,
    c.git_branch,
    c.started_at,
    c.ended_at,
    c.message_count,
    COUNT(te.id) as technical_event_count,
    EXTRACT(EPOCH FROM (c.ended_at - c.started_at))/60 as duration_minutes
FROM conversations c
LEFT JOIN technical_events te ON c.id = te.conversation_id
GROUP BY c.id, c.project_name, c.session_id, c.git_branch, 
         c.started_at, c.ended_at, c.message_count;

-- Recent activity view
CREATE VIEW recent_activity AS
SELECT 
    c.project_name,
    c.session_id,
    c.started_at,
    c.message_count,
    te.event_type,
    te.file_path,
    te.timestamp as event_time
FROM conversations c
JOIN technical_events te ON c.id = te.conversation_id
WHERE c.started_at > NOW() - INTERVAL '30 days'
ORDER BY te.timestamp DESC;

-- Grant permissions to application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO claude_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO claude_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO claude_user;

-- Initial database stats
INSERT INTO conversations (project_name, project_path, session_id, file_path, message_count) 
VALUES ('__system__', '__system__', 'init', '__init__', 0);

-- Log successful initialization
DO $$ 
BEGIN 
    RAISE NOTICE 'Claude Conversation Analyzer database initialized successfully';
    RAISE NOTICE 'pgvector extension: %', (SELECT installed_version FROM pg_available_extensions WHERE name = 'vector');
END $$;