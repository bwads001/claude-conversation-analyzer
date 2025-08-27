# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Conversation Analyzer - A semantic search and timeline analysis tool for Claude Code conversation history. Processes JSONL conversation files to build a searchable knowledge base with PostgreSQL + pgvector for hybrid SQL and vector search.

## Development Commands

### Database Setup
```bash
# Start PostgreSQL with pgvector extension
docker-compose -f config/docker-compose.yml up -d

# Initialize database schema
python scripts/init_db.py
```

### Core Development
```bash
# Install dependencies
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Set up Ollama embedding model (required)
ollama pull nomic-embed-text  # Primary choice: 768 dimensions
# ollama pull mxbai-embed-large  # Alternative: 1024 dimensions

# Import conversation data
python scripts/ingest_flexible.py --all

# Search conversations
python scripts/search_cli.py "your search query"
python scripts/search_cli.py "database optimization" --project "my-project"
python scripts/search_cli.py "AWS issues" --after "2025-08-01"
```

### Testing
```bash
# Run with test data (when implemented)
python scripts/ingest_flexible.py --project-path setup/test_data/
python scripts/search_cli.py "test query"
```

## Architecture

**Data Flow:** Claude JSONL Files → Parser → PostgreSQL + pgvector → Search Interface  
**Embeddings:** Local Ollama with `nomic-embed-text` (768 dims) for privacy  
**Database:** PostgreSQL with pgvector extension for hybrid search

### Key Components

- **src/parser.py**: JSONL conversation parsing with metadata extraction
- **src/embeddings.py**: Ollama integration for local embeddings
- **src/database.py**: PostgreSQL + pgvector operations with bulk inserts
- **scripts/ingest_flexible.py**: Flexible data ingestion with multiple options
- **scripts/search_cli.py**: Command-line semantic search interface

### Database Schema

Primary tables: `conversations` (metadata), `messages` (content + embeddings), `technical_events` (extracted events)  
Uses pgvector with IVFFlat indexes for efficient similarity search  
Designed for ~50K-200K messages with 1-5GB total database size

## Implementation Priority

**Phase 1 (Current Focus):**
1. JSONL parser for Claude conversation files
2. Ollama embedding pipeline with batching
3. PostgreSQL + pgvector setup with schema
4. Basic semantic search CLI

**Critical JSONL Parsing Notes:**
- First message often lacks timestamp - use next message or file mtime
- Content can be string or array of blocks
- Extract tool uses for technical event tracking
- Handle project classification from directory structure

## Technical Decisions

**PostgreSQL + pgvector** chosen over pure vector databases for hybrid SQL + semantic search capabilities  
**Ollama local embeddings** for privacy and no API costs (GPU accelerated)  
**Project classification** uses Claude's existing directory structure from `~/.claude/projects/`  
**Vector similarity thresholds:** <0.3 very similar, <0.5 relevant, <0.7 somewhat related

## Test Data Location

User conversation files: `~/.claude/projects/` with encoded project subdirectories  
Test data: `setup/test_data/` (for development)

## Dependencies

- Docker & Docker Compose for PostgreSQL
- Python 3.10+ with asyncpg, numpy
- Ollama with embedding model locally installed
- NVIDIA GPU recommended for embeddings (CPU works)

## Development Notes

This project is designed to help Claude Code users better manage their conversation history through semantic search and timeline analysis. The system processes JSONL conversation files from `~/.claude/projects/` to create a searchable knowledge base.