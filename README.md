# Claude Conversation Analyzer

A semantic search and timeline analysis tool for Claude Code conversation history. Build a searchable knowledge base from your AI pair programming sessions, track technical accomplishments over time, and generate work journals for performance reviews.

**Now with Web Interface!** - Search your conversations with a modern React UI and explore results with full conversation context.

## 🎯 Problem Statement

When using Claude Code across multiple sessions and projects, valuable technical context gets fragmented across numerous JSONL files. This tool solves:

- **Lost Context**: "I know we solved this database issue last month, but which conversation was it?"
- **Timeline Reconstruction**: "What did I actually accomplish in Week 3 for my performance review?"
- **Cross-Project Patterns**: "Show me all the performance optimization work across all projects"
- **Technical Knowledge Mining**: "Find all conversations where we debugged compilation errors"

## 🚀 Features

### Core Functionality
- **Semantic Search**: Find conversations by meaning, not just keywords  
- **Timeline Analysis**: Chronological view of technical work across sessions
- **Project-Based Organization**: Leverages Claude's existing project structure
- **Local Processing**: All data stays on your machine, using local Ollama embeddings
- **Work Journal Generation**: Automated technical accomplishment summaries
- **Hybrid Search**: Combine semantic similarity with SQL filters (date ranges, projects, file types)

### Web Interface (NEW!)
- **Modern React UI**: Clean, responsive interface for searching conversations
- **Result Cards**: Visual search results with similarity scores and context
- **Conversation Viewer**: Click any result to see full conversation context
- **Smart Context**: View messages around matches or full conversations  
- **Advanced Filters**: Filter by project, date range, role, similarity threshold
- **Syntax Highlighting**: Code blocks and tool uses properly formatted
- **Real-time Search**: Powered by semantic embeddings for intelligent matching

## 🏗️ Architecture

```
Claude JSONL Files → Parser → PostgreSQL + pgvector → FastAPI → React UI
                         ↓                              ↓
                    Ollama Embeddings              Command Line
                    (local GPU accelerated)
```

### Technology Stack
- **Database**: PostgreSQL with pgvector extension for hybrid SQL + vector search
- **Embeddings**: Ollama with models like `nomic-embed-text` (768 dims) or `mxbai-embed-large` (1024 dims)  
- **Backend**: Python with asyncpg, numpy, and FastAPI
- **Frontend**: React + TypeScript with Vite, Tailwind CSS, and React Query
- **CLI Tools**: Python scripts for ingestion and command-line search
- **Container**: Docker Compose for PostgreSQL + pgvector

## 📋 Requirements

### Quick Start (Docker Setup)
- **Docker Desktop** (Windows/Mac) or **Docker + Docker Compose** (Linux)
- **Ollama** with `nomic-embed-text` model
- ~2GB disk space for database (grows with conversation history)
- Modern web browser

### Optional for GPU Acceleration
- NVIDIA GPU with drivers (greatly improves embedding speed)

### Manual Development Setup  
- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL with pgvector (or use Docker)

## 🛠️ Installation

**Easy Docker Setup (Recommended for beginners)**

1. **Clone the repository**
```bash
git clone https://github.com/bwads001/claude-conversation-analyzer
cd claude-conversation-analyzer
```

2. **Run the interactive setup**
```bash
chmod +x setup.sh
./setup.sh
```
The setup script will:
- Check system requirements (Docker, Ollama)
- Find your Claude conversation files automatically
- Configure the environment
- Pull required Docker images
- Initialize the database

3. **Start all services**
```bash
./start.sh
```
This will start PostgreSQL, the API server, and web interface in Docker containers.

4. **Open your browser to [http://localhost:3000](http://localhost:3000)**

---

**Manual Installation (For developers)**

<details>
<summary>Click to expand manual installation steps</summary>

1. **Clone and navigate**
```bash
git clone https://github.com/bwads001/claude-conversation-analyzer
cd claude-conversation-analyzer
```

2. **Copy environment configuration**
```bash
cp .env.example .env
# Edit .env with your Claude data path and preferences
```

3. **Start with Docker Compose**
```bash
docker-compose -f config/docker-compose.yml up -d
```

4. **Alternative: Local development setup**
```bash
# Start PostgreSQL only
docker-compose -f config/docker-compose.yml up -d postgres

# Install Python dependencies
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Install Ollama and pull embedding model
ollama pull nomic-embed-text

# Initialize database and ingest conversations
python scripts/init_db.py
python scripts/ingest_flexible.py --all

# Start development servers
./start-dev.sh  # Starts API + web frontend
```

</details>

## 🔍 Usage

### Web Interface (Recommended)

After running `./start.sh`, your Claude Conversation Analyzer will be ready at **http://localhost:3000**.

**Search Features:**
- Enter keywords like "database performance", "React components", "error handling"  
- Use the filter icon to narrow by project, date range, or role
- Click result cards to see full conversation context
- Switch between context view (messages around match) and full conversation

**Example Searches:**
- `"API error handling"` - Find conversations about error management
- `"performance optimization"` - Discover performance-related discussions  
- `"database migration"` - Search for database-related work
- `"React component design"` - Find frontend development conversations

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
    role TEXT,  -- 'user', 'assistant', 'tool', 'system', or 'summary'
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