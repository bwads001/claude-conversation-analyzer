"""
Claude Conversation Analyzer - Semantic search for Claude Code conversation history.
"""

__version__ = "0.1.0"
__author__ = "Claude Code Community"

from .parser import JSONLParser, parse_conversation_files
from .database import ConversationDatabase, DatabaseConfig
from .embeddings import OllamaEmbeddings, EmbeddingConfig

__all__ = [
    "JSONLParser",
    "parse_conversation_files", 
    "ConversationDatabase",
    "DatabaseConfig",
    "OllamaEmbeddings",
    "EmbeddingConfig"
]