#!/usr/bin/env python3
"""
FastAPI backend for Claude Conversation Analyzer web interface.
"""

import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import asyncio

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import ConversationDatabase, DatabaseConfig
from embeddings import OllamaEmbeddings

app = FastAPI(
    title="Claude Conversation Analyzer API",
    description="Search and analyze Claude Code conversation history",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
db_config = DatabaseConfig(
    host="localhost",
    port=5433,
    database="claude_conversations",
    username="claude_user",
    password="claude_pass"
)

# Response models
class SearchResult(BaseModel):
    id: str
    content: str
    role: str
    timestamp: Optional[datetime]
    project_name: str
    git_branch: Optional[str]
    similarity: float
    conversation_id: str

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query: str

class Message(BaseModel):
    id: str
    role: str
    content: str
    timestamp: Optional[datetime]
    tool_uses: Optional[dict] = None

class Conversation(BaseModel):
    id: str
    project_name: str
    session_id: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    git_branch: Optional[str]
    messages: List[Message]

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "Claude Conversation Analyzer API"}

@app.get("/api/search", response_model=SearchResponse)
async def search_conversations(
    q: str = Query(..., description="Search query"),
    project: Optional[str] = Query(None, description="Filter by project"),
    date_after: Optional[str] = Query(None, alias="dateAfter", description="Filter after date (YYYY-MM-DD)"),
    date_before: Optional[str] = Query(None, alias="dateBefore", description="Filter before date (YYYY-MM-DD)"),
    role: Optional[str] = Query(None, description="Filter by role (user/assistant/system)"),
    threshold: Optional[float] = Query(0.7, description="Similarity threshold (0-1)"),
    limit: Optional[int] = Query(20, description="Maximum results")
):
    """Search conversations using semantic similarity."""
    
    db = ConversationDatabase(db_config)
    embeddings = OllamaEmbeddings()
    
    try:
        await db.initialize()
        
        # Check if embedding model is available
        if not await embeddings.is_model_available():
            raise HTTPException(status_code=503, detail="Embedding model not available")
        
        # Generate query embedding
        query_embedding = await embeddings.embed_single(q)
        
        # Parse date filters
        date_after_dt = None
        date_before_dt = None
        if date_after:
            date_after_dt = datetime.strptime(date_after, "%Y-%m-%d")
        if date_before:
            date_before_dt = datetime.strptime(date_before, "%Y-%m-%d")
        
        # Search database
        results = await db.search_similar(
            query_embedding,
            limit=limit,
            similarity_threshold=threshold,
            project_filter=project,
            date_after=date_after_dt,
            date_before=date_before_dt
        )
        
        # Convert to response format
        search_results = [
            SearchResult(
                id=result['id'],
                content=result['content'],
                role=result['role'],
                timestamp=result['timestamp'],
                project_name=result['project_name'],
                git_branch=result.get('git_branch'),
                similarity=result['similarity'],
                conversation_id=result['conversation_id']
            )
            for result in results
        ]
        
        return SearchResponse(
            results=search_results,
            total=len(search_results),
            query=q
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()
        await embeddings.close()

@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get full conversation by ID."""
    
    db = ConversationDatabase(db_config)
    
    try:
        await db.initialize()
        
        async with db.get_connection() as conn:
            # Get conversation metadata
            conv_result = await conn.fetchrow("""
                SELECT id, project_name, session_id, started_at, ended_at, git_branch
                FROM conversations 
                WHERE id = $1
            """, conversation_id)
            
            if not conv_result:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            # Get all messages for this conversation
            message_results = await conn.fetch("""
                SELECT id, role, content, timestamp, tool_uses
                FROM messages 
                WHERE conversation_id = $1
                ORDER BY timestamp ASC, created_at ASC
            """, conversation_id)
            
            messages = [
                Message(
                    id=str(msg['id']),
                    role=msg['role'],
                    content=msg['content'],
                    timestamp=msg['timestamp'],
                    tool_uses=msg['tool_uses']
                )
                for msg in message_results
            ]
            
            return Conversation(
                id=str(conv_result['id']),
                project_name=conv_result['project_name'],
                session_id=conv_result['session_id'],
                started_at=conv_result['started_at'],
                ended_at=conv_result['ended_at'],
                git_branch=conv_result['git_branch'],
                messages=messages
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()

@app.get("/api/conversations/{conversation_id}/context", response_model=Conversation)
async def get_conversation_context(
    conversation_id: str,
    message_id: str = Query(..., alias="messageId", description="Message ID to center context around"),
    context_size: int = Query(10, alias="contextSize", description="Number of messages before/after")
):
    """Get conversation context around a specific message."""
    
    db = ConversationDatabase(db_config)
    
    try:
        await db.initialize()
        
        async with db.get_connection() as conn:
            # Get conversation metadata
            conv_result = await conn.fetchrow("""
                SELECT id, project_name, session_id, started_at, ended_at, git_branch
                FROM conversations 
                WHERE id = $1
            """, conversation_id)
            
            if not conv_result:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            # Get messages around the target message
            message_results = await conn.fetch("""
                WITH target_message AS (
                    SELECT row_number() OVER (ORDER BY timestamp ASC, created_at ASC) as rn
                    FROM messages 
                    WHERE conversation_id = $1 AND id = $2
                ),
                message_window AS (
                    SELECT 
                        m.id, m.role, m.content, m.timestamp, m.tool_uses,
                        row_number() OVER (ORDER BY timestamp ASC, created_at ASC) as rn
                    FROM messages m
                    WHERE conversation_id = $1
                )
                SELECT mw.id, mw.role, mw.content, mw.timestamp, mw.tool_uses
                FROM message_window mw, target_message tm
                WHERE mw.rn BETWEEN (tm.rn - $3) AND (tm.rn + $3)
                ORDER BY mw.rn
            """, conversation_id, message_id, context_size)
            
            messages = [
                Message(
                    id=str(msg['id']),
                    role=msg['role'],
                    content=msg['content'],
                    timestamp=msg['timestamp'],
                    tool_uses=msg['tool_uses']
                )
                for msg in message_results
            ]
            
            return Conversation(
                id=str(conv_result['id']),
                project_name=conv_result['project_name'],
                session_id=conv_result['session_id'],
                started_at=conv_result['started_at'],
                ended_at=conv_result['ended_at'],
                git_branch=conv_result['git_branch'],
                messages=messages
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()

@app.get("/api/projects", response_model=List[str])
async def get_projects():
    """Get list of all project names."""
    
    db = ConversationDatabase(db_config)
    
    try:
        await db.initialize()
        
        async with db.get_connection() as conn:
            results = await conn.fetch("""
                SELECT DISTINCT project_name 
                FROM conversations 
                WHERE project_name != '__system__'
                ORDER BY project_name
            """)
            
            return [row['project_name'] for row in results]
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)