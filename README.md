# Claude Conversation Analyzer

A semantic search and timeline analysis tool for Claude Code conversation history. Build a searchable knowledge base from your AI pair programming sessions, track technical accomplishments over time, and generate work journals for performance reviews.

## 🎯 Problem Statement

When using Claude Code across multiple sessions and projects, valuable technical context gets fragmented across numerous JSONL files. This tool solves:

- **Lost Context**: "I know we solved this database issue last month, but which conversation was it?"
- **Timeline Reconstruction**: "What did I actually accomplish in Week 3 for my performance review?"
- **Cross-Project Patterns**: "Show me all the performance optimization work across all projects"
- **Technical Knowledge Mining**: "Find all conversations where we debugged compilation errors"

## 🚀 Features

- **Semantic Search**: Find conversations by meaning, not just keywords
- **Timeline Analysis**: Chronological view of technical work across sessions
- **Project-Based Organization**: Leverages Claude's existing project structure
- **Local Processing**: All data stays on your machine, using local Ollama embeddings
- **Work Journal Generation**: Automated technical accomplishment summaries
- **Hybrid Search**: Combine semantic similarity with SQL filters (date ranges, projects, file types)

## 🏗️ Architecture

```
Claude JSONL Files → Parser → PostgreSQL + pgvector → Search Interface
                         ↓
                    Ollama Embeddings
                    (local GPU accelerated)
```

### Technology Stack
- **Database**: PostgreSQL with pgvector extension for hybrid SQL + vector search
- **Embeddings**: Ollama with models like `nomic-embed-text` (768 dims) or `mxbai-embed-large` (1024 dims)
- **Backend**: Python with asyncpg, numpy, and FastAPI
- **Frontend**: (Optional) Web UI for search and visualization
- **Container**: Docker Compose for PostgreSQL + pgvector

## 📋 Requirements

- Docker & Docker Compose
- Python 3.10+
- Ollama installed locally with an embedding model
- NVIDIA GPU recommended (but CPU works too)
- ~2GB disk space for database (grows with conversation history)

## 🛠️ Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/claude-conversation-analyzer
cd claude-conversation-analyzer
```

2. **Start PostgreSQL with pgvector**
```bash
docker-compose up -d
```

3. **Install Python dependencies**
```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

4. **Pull an embedding model for Ollama**
```bash
ollama pull nomic-embed-text  # Recommended: good balance of speed/quality
# or
ollama pull mxbai-embed-large  # Better quality, slower
```

5. **Initialize the database**
```bash
python scripts/init_db.py
```

6. **Import your conversation history**
```bash
python scripts/ingest.py ~/.claude/projects/
```

## 🔍 Usage

### Command Line Search
```bash
# Semantic search across all conversations
python scripts/search_cli.py "database performance optimization"

# Filter by project
python scripts/search_cli.py "compilation errors" --project "MyProject"

# Filter by date range
python scripts/search_cli.py "AWS infrastructure" --after "2025-08-01" --before "2025-08-31"

# Find similar conversations to a specific error
python scripts/search_cli.py --similar-to "error: package com.example.data does not exist"
```

### Generate Work Journal
```bash
# Generate journal for specific week
python scripts/generate_journal.py --week "2025-W34"

# Generate monthly summary
python scripts/generate_journal.py --month "2025-08"

# Export for performance review
python scripts/generate_journal.py --format markdown --output ~/work-journal-august.md
```

### Web Interface (Optional)
```bash
python web/app.py
# Open http://localhost:8000
```

## 📊 Database Schema

```sql
-- Main tables
conversations (
    id UUID PRIMARY KEY,
    project_name TEXT,
    session_id TEXT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    git_branch TEXT,
    metadata JSONB
)

messages (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations,
    role TEXT,  -- 'user' or 'assistant'
    content TEXT,
    embedding vector(768),  -- Semantic search vector
    timestamp TIMESTAMP,
    tool_uses JSONB  -- Structured data about tool calls
)

technical_events (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations,
    event_type TEXT,  -- 'file_created', 'error_resolved', 'test_passed', etc.
    details JSONB,
    timestamp TIMESTAMP
)

-- Indexes for performance
CREATE INDEX ON messages USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON conversations (project_name, started_at);
CREATE INDEX ON technical_events (event_type, timestamp);
```

## 🎯 Planned Features

### Phase 1: Core Functionality (Current Focus)
- [x] Project structure and setup
- [ ] JSONL parser for Claude conversations
- [ ] Ollama embedding integration
- [ ] PostgreSQL + pgvector setup
- [ ] Basic semantic search CLI
- [ ] Timeline extraction

### Phase 2: Enhanced Search
- [ ] Hybrid search (semantic + keyword + filters)
- [ ] Search result ranking improvements
- [ ] Code snippet extraction
- [ ] Error pattern recognition

### Phase 3: Analysis & Reporting
- [ ] Automated work journal generation
- [ ] Technical accomplishment summaries
- [ ] Cross-project pattern analysis
- [ ] Performance metric extraction

### Phase 4: User Interface
- [ ] Web-based search interface
- [ ] Timeline visualization
- [ ] Project relationship graphs
- [ ] Export capabilities (Markdown, JSON, CSV)

## 🤝 Contributing

Contributions are welcome! This tool is designed to help the Claude Code community better manage their conversation history.

### Areas for Contribution
- Additional embedding model support
- Alternative vector databases (Qdrant, ChromaDB)
- Search UI improvements
- Analysis algorithms
- Documentation and examples

## 🔒 Privacy & Security

- **100% Local**: No data leaves your machine
- **No Telemetry**: No usage tracking or analytics
- **Customizable**: Remove or redact sensitive information before indexing
- **Open Source**: Audit the code yourself

## 📝 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Built to solve real pain points from extensive Claude Code usage
- Inspired by the need for better knowledge management in AI pair programming
- Thanks to the pgvector and Ollama communities for excellent tools

## 📧 Contact

- GitHub Issues: [Report bugs or request features](https://github.com/yourusername/claude-conversation-analyzer/issues)
- Discussions: [Share your use cases and ideas](https://github.com/yourusername/claude-conversation-analyzer/discussions)

---

**Note**: This project is not affiliated with Anthropic or Claude. It's a community tool for managing conversation history from Claude Code (claude.ai/code).