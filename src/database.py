"""
Database layer for Claude Conversation Analyzer.

Handles PostgreSQL operations with pgvector for semantic search.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from uuid import UUID, uuid4

import asyncpg
import numpy as np
from asyncpg import Connection, Pool

try:
    from .parser import ConversationMetadata, ParsedMessage
except ImportError:
    from parser import ConversationMetadata, ParsedMessage

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration settings."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "claude_conversations",
        username: str = "claude_user",
        password: str = "claude_pass",
        min_connections: int = 1,
        max_connections: int = 10
    ):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections
    
    @property
    def dsn(self) -> str:
        """Database connection string."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class ConversationDatabase:
    """Database operations for conversation storage and search."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool: Optional[Pool] = None
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.config.dsn,
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                command_timeout=60
            )
            self.logger.info("Database connection pool initialized")
            
            # Test connection and ensure extensions are available
            async with self.pool.acquire() as conn:
                # Check pgvector extension
                result = await conn.fetchval(
                    "SELECT installed_version FROM pg_available_extensions WHERE name = 'vector'"
                )
                if not result:
                    raise RuntimeError("pgvector extension not available")
                
                self.logger.info(f"pgvector extension version: {result}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.logger.info("Database connection pool closed")
    
    async def create_schema(self):
        """Create database schema from SQL file."""
        from pathlib import Path
        
        # Read the schema SQL file
        sql_file = Path(__file__).parent.parent / "scripts" / "init_db.sql"
        if not sql_file.exists():
            raise FileNotFoundError(f"Schema file not found: {sql_file}")
        
        schema_sql = sql_file.read_text()
        
        async with self.get_connection() as conn:
            # Execute the schema creation SQL
            await conn.execute(schema_sql)
            self.logger.info("Database schema created successfully")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool."""
        if not self.pool:
            raise RuntimeError("Database not initialized")
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def store_conversation(
        self, 
        conversation: ConversationMetadata, 
        messages: List[ParsedMessage],
        embeddings: Optional[List[np.ndarray]] = None
    ) -> UUID:
        """
        Store a conversation with its messages in the database.
        
        Args:
            conversation: Conversation metadata
            messages: List of parsed messages
            embeddings: Optional list of embedding vectors for messages
            
        Returns:
            UUID of stored conversation
        """
        if embeddings and len(embeddings) != len(messages):
            raise ValueError("Number of embeddings must match number of messages")
        
        async with self.get_connection() as conn:
            async with conn.transaction():
                # Insert conversation (skip if exists)
                conversation_id = await conn.fetchval("""
                    INSERT INTO conversations (
                        project_name, project_path, session_id, git_branch,
                        started_at, ended_at, working_directory, message_count,
                        metadata, file_path
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (session_id, file_path) DO UPDATE SET
                        message_count = EXCLUDED.message_count,
                        updated_at = NOW()
                    RETURNING id
                """, 
                    conversation.project_name,
                    conversation.project_path,
                    conversation.session_id,
                    conversation.git_branch,
                    conversation.started_at,
                    conversation.ended_at,
                    conversation.working_directory,
                    len(messages),
                    json.dumps({}),  # metadata JSONB
                    conversation.file_path
                )
                
                # Prepare message data for bulk insert
                message_data = []
                technical_events = []
                
                for i, msg in enumerate(messages):
                    # Convert numpy array to string format for pgvector
                    if embeddings and embeddings[i] is not None:
                        vector_list = embeddings[i].tolist()
                        embedding_vector = f"[{','.join(map(str, vector_list))}]"
                    else:
                        embedding_vector = None
                    
                    message_data.append((
                        conversation_id,
                        msg.uuid,
                        msg.role,
                        msg.content,
                        embedding_vector,
                        msg.timestamp,
                        json.dumps(msg.tool_uses) if msg.tool_uses else None,
                        json.dumps(msg.metadata) if msg.metadata else None
                    ))
                    
                    # Extract technical events if tool uses present
                    if msg.tool_uses:
                        try:
                            event_type = self._extract_event_type(msg.tool_uses)
                            if event_type:
                                # Get file_path safely
                                file_path = None
                                if isinstance(msg.tool_uses, dict):
                                    file_path = msg.tool_uses.get('file_path') or msg.tool_uses.get('filePath')
                                
                                technical_events.append((
                                    conversation_id,
                                    msg.uuid,  # We'll update with actual message_id after insert
                                    event_type,
                                    file_path,
                                    msg.tool_uses,
                                    msg.timestamp
                                ))
                        except Exception as e:
                            print(f"Error processing tool_uses for message {msg.uuid}: {e}")
                            print(f"tool_uses type: {type(msg.tool_uses)}")
                            print(f"tool_uses value: {msg.tool_uses}")
                            raise
                
                # Bulk insert messages with conflict resolution
                inserted_messages = await conn.fetch("""
                    INSERT INTO messages (
                        conversation_id, message_uuid, role, content, embedding,
                        timestamp, tool_uses, metadata
                    ) 
                    SELECT * FROM UNNEST($1::uuid[], $2::text[], $3::text[], 
                                       $4::text[], $5::vector[], $6::timestamptz[], 
                                       $7::jsonb[], $8::jsonb[])
                    ON CONFLICT (conversation_id, message_uuid) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        updated_at = NOW()
                    RETURNING id, message_uuid
                """, *zip(*message_data) if message_data else ([], [], [], [], [], [], [], []))
                
                # Create mapping from message_uuid to message_id for technical events
                uuid_to_id = {row['message_uuid']: row['id'] for row in inserted_messages}
                
                # Insert technical events with correct message_ids
                if technical_events:
                    technical_event_data = []
                    for conv_id, msg_uuid, event_type, file_path, details, timestamp in technical_events:
                        if msg_uuid in uuid_to_id:
                            technical_event_data.append((
                                conv_id, uuid_to_id[msg_uuid], event_type, 
                                file_path, json.dumps(details), timestamp
                            ))
                    
                    if technical_event_data:
                        await conn.executemany("""
                            INSERT INTO technical_events (
                                conversation_id, message_id, event_type, 
                                file_path, details, timestamp
                            ) VALUES ($1, $2, $3, $4, $5, $6)
                        """, technical_event_data)
                
                self.logger.info(f"Stored conversation {conversation_id} with {len(messages)} messages")
                return conversation_id
    
    async def create_vector_index(self, lists: int = 100):
        """
        Create vector similarity index after data is loaded.
        
        Args:
            lists: Number of cluster centers for IVFFlat index
        """
        async with self.get_connection() as conn:
            # Check if index already exists
            index_exists = await conn.fetchval("""
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'messages' AND indexname = 'idx_messages_embedding'
            """)
            
            if index_exists:
                self.logger.info("Vector index already exists")
                return
            
            # Create the index
            self.logger.info(f"Creating vector index with {lists} lists...")
            await conn.execute(f"""
                CREATE INDEX idx_messages_embedding ON messages 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = {lists})
            """)
            self.logger.info("Vector index created successfully")
    
    async def search_similar(
        self, 
        query_embedding: np.ndarray, 
        limit: int = 10,
        similarity_threshold: float = 0.7,
        project_filter: Optional[str] = None,
        date_after: Optional[datetime] = None,
        date_before: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar messages using vector similarity.
        
        Args:
            query_embedding: Query vector for similarity search
            limit: Maximum number of results
            similarity_threshold: Maximum cosine distance (lower = more similar)
            project_filter: Optional project name filter
            date_after: Optional date filter (after)
            date_before: Optional date filter (before)
            
        Returns:
            List of similar messages with metadata
        """
        # Build dynamic query with filters  
        where_conditions = ["m.embedding IS NOT NULL"]
        # Convert query embedding to pgvector string format
        query_vector_str = f"[{','.join(map(str, query_embedding.tolist()))}]"
        params = [query_vector_str, similarity_threshold, limit]
        param_idx = 4
        
        if project_filter:
            where_conditions.append(f"c.project_name = ${param_idx}")
            params.append(project_filter)
            param_idx += 1
        
        if date_after:
            where_conditions.append(f"m.timestamp >= ${param_idx}")
            params.append(date_after)
            param_idx += 1
            
        if date_before:
            where_conditions.append(f"m.timestamp <= ${param_idx}")
            params.append(date_before)
            param_idx += 1
        
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
            SELECT 
                m.id,
                m.content,
                m.role,
                m.timestamp,
                m.embedding <=> $1 as similarity,
                c.project_name,
                c.session_id,
                c.git_branch,
                c.file_path
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE {where_clause}
              AND m.embedding <=> $1 < $2
            ORDER BY m.embedding <=> $1
            LIMIT $3
        """
        
        async with self.get_connection() as conn:
            results = await conn.fetch(query, *params)
            
            return [
                {
                    'id': str(row['id']),
                    'content': row['content'],
                    'role': row['role'],
                    'timestamp': row['timestamp'],
                    'similarity': float(row['similarity']),
                    'project_name': row['project_name'],
                    'session_id': row['session_id'],
                    'git_branch': row['git_branch'],
                    'file_path': row['file_path']
                }
                for row in results
            ]
    
    async def get_conversation_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        async with self.get_connection() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(DISTINCT c.id) as conversation_count,
                    COUNT(m.id) as message_count,
                    COUNT(DISTINCT c.project_name) as project_count,
                    COUNT(CASE WHEN m.embedding IS NOT NULL THEN 1 END) as embedded_message_count,
                    COUNT(te.id) as technical_event_count,
                    MIN(c.started_at) as earliest_conversation,
                    MAX(c.ended_at) as latest_conversation
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                LEFT JOIN technical_events te ON c.id = te.conversation_id
                WHERE c.session_id != 'init'  -- Exclude init record
            """)
            
            return dict(stats) if stats else {}
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get list of all projects with conversation counts."""
        async with self.get_connection() as conn:
            projects = await conn.fetch("""
                SELECT 
                    c.project_name,
                    COUNT(c.id) as conversation_count,
                    COUNT(m.id) as message_count,
                    MIN(c.started_at) as first_conversation,
                    MAX(c.ended_at) as latest_conversation
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.session_id != 'init'
                GROUP BY c.project_name
                ORDER BY latest_conversation DESC NULLS LAST
            """)
            
            return [dict(row) for row in projects]
    
    def _extract_event_type(self, tool_uses: Dict[str, Any]) -> Optional[str]:
        """Extract standardized event type from tool use data."""
        if not tool_uses:
            return None
        
        # Handle real Claude conversation format
        # The tool_uses comes from 'toolUseResult' field which has different structure
        # For now, just categorize based on content
        if 'newTodos' in tool_uses or 'oldTodos' in tool_uses:
            return 'todo_updated'
        elif 'content' in tool_uses:
            return 'tool_result'
        else:
            return 'tool_use'


async def test_database_connection(config: DatabaseConfig):
    """Test database connectivity and basic operations."""
    db = ConversationDatabase(config)
    
    try:
        await db.initialize()
        
        # Test basic query
        async with db.get_connection() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1
            
        # Get stats
        stats = await db.get_conversation_stats()
        logger.info(f"Database stats: {stats}")
        
        logger.info("Database connection test successful")
        
    finally:
        await db.close()


if __name__ == "__main__":
    # Quick connection test
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    config = DatabaseConfig()
    
    try:
        asyncio.run(test_database_connection(config))
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)