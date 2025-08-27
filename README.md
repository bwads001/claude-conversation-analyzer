# Claude Conversation Analyzer

Search your Claude Code conversation history with semantic AI-powered search. Build a searchable knowledge base from all your AI pair programming sessions.

## 🎯 What This Solves

- **"I know we solved this last month, but which conversation?"** - Find conversations by meaning, not just keywords
- **"What did I accomplish this week?"** - Track your technical progress over time  
- **"Show me all React work across projects"** - Search across all your conversations at once

## ✨ Features

- **Smart Search**: Find conversations by topic, not just exact words
- **Web Interface**: Modern, clean interface for browsing results
- **100% Local**: Your conversations never leave your computer
- **Project Organization**: Automatically organizes by your Claude projects
- **Privacy First**: No tracking, no telemetry, no external API calls

## 🚀 Quick Start

1. **Clone and setup**
```bash
git clone https://github.com/bwads001/claude-conversation-analyzer
cd claude-conversation-analyzer
chmod +x setup.sh
./setup.sh
```

2. **Start the app**  
```bash
./start.sh
```

3. **Open http://localhost:3000** and start searching!

## 📋 Requirements

- **Docker Desktop** (Windows/Mac) or **Docker + Docker Compose** (Linux)
- **Ollama** with the `nomic-embed-text` model
- ~2GB disk space for your conversation database

## 🔍 Example Searches

- `"database performance issues"`
- `"React component patterns"`
- `"error handling best practices"`
- `"AWS deployment problems"`

## 🔒 Privacy

- **100% Local**: No data leaves your machine
- **No Telemetry**: Zero tracking or analytics
- **Open Source**: Audit the code yourself

## 📝 License

MIT License - See LICENSE file for details

---

**Note**: This project is not affiliated with Anthropic or Claude. It's a community tool for managing conversation history from Claude Code (claude.ai/code).