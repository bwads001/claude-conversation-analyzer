#!/usr/bin/env python3
"""
Main ingestion script for Claude Conversation Analyzer.

Processes Claude conversation JSONL files, generates embeddings,
and stores everything in PostgreSQL with pgvector.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional
import click

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parser import parse_conversation_files
from database import ConversationDatabase, DatabaseConfig
from embeddings import OllamaEmbeddings, EmbeddingConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def ingest_conversations(
    input_path: Path,
    db_config: DatabaseConfig,
    embedding_config: EmbeddingConfig,
    dry_run: bool = False
):
    """
    Main ingestion pipeline.
    
    Args:
        input_path: Directory containing conversation files
        db_config: Database configuration
        embedding_config: Embedding configuration
        dry_run: If True, parse and generate embeddings but don't store
    """
    logger.info(f"Starting ingestion from {input_path}")
    
    # Step 1: Parse conversation files
    logger.info("📁 Parsing conversation files...")
    try:
        conversations, messages = parse_conversation_files(input_path)
        logger.info(f"Parsed {len(conversations)} conversations with {len(messages)} messages")
    except Exception as e:
        logger.error(f"Failed to parse conversations: {e}")
        raise
    
    if not conversations:
        logger.warning("No conversations found to process")
        return
    
    # Step 2: Generate embeddings
    logger.info("🤖 Generating embeddings...")
    embeddings = []
    
    async with OllamaEmbeddings(embedding_config) as embedder:
        # Check model availability
        if not await embedder.is_model_available():
            raise RuntimeError(f"Ollama model {embedding_config.model} not available")
        
        # Extract message contents for embedding
        message_contents = [msg.content for msg in messages]
        embeddings = await embedder.embed_conversations(message_contents)
        
        logger.info(f"Generated {len(embeddings)} embeddings")
    
    if dry_run:
        logger.info("🔍 Dry run complete - no data stored")
        print_summary(conversations, messages, embeddings)
        return
    
    # Step 3: Store in database
    logger.info("💾 Storing in database...")
    
    db = ConversationDatabase(db_config)
    await db.initialize()
    
    try:
        # Group messages by conversation for storage
        conversations_dict = {conv.session_id: conv for conv in conversations}
        current_conversation = None
        current_messages = []
        current_embeddings = []
        stored_count = 0
        
        for i, message in enumerate(messages):
            # Extract conversation info from message metadata or find matching conversation
            message_conversation = None
            for conv in conversations:
                # This is a simplified match - in practice you'd match by file path or session
                if conv.session_id in message.metadata.get('source_file', ''):
                    message_conversation = conv
                    break
            
            # If we can't match, use first conversation (fallback)
            if not message_conversation:
                message_conversation = conversations[0]
            
            if current_conversation is None or current_conversation.session_id != message_conversation.session_id:
                # Store previous conversation if exists
                if current_conversation and current_messages:
                    await db.store_conversation(
                        current_conversation, 
                        current_messages, 
                        current_embeddings
                    )
                    stored_count += 1
                
                # Start new conversation
                current_conversation = message_conversation
                current_messages = [message]
                current_embeddings = [embeddings[i]]
            else:
                current_messages.append(message)
                current_embeddings.append(embeddings[i])
        
        # Store final conversation
        if current_conversation and current_messages:
            await db.store_conversation(
                current_conversation,
                current_messages, 
                current_embeddings
            )
            stored_count += 1
        
        logger.info(f"Stored {stored_count} conversations")
        
        # Create vector index for efficient similarity search
        logger.info("🔍 Creating vector search index...")
        await db.create_vector_index()
        
        # Print final stats
        stats = await db.get_conversation_stats()
        logger.info("✅ Ingestion complete!")
        print_database_stats(stats)
        
    finally:
        await db.close()


def print_summary(conversations, messages, embeddings):
    """Print ingestion summary."""
    print("\n" + "="*60)
    print("📊 INGESTION SUMMARY")
    print("="*60)
    print(f"Conversations: {len(conversations)}")
    print(f"Messages: {len(messages)}")
    print(f"Embeddings: {len(embeddings)}")
    
    if conversations:
        projects = set(conv.project_name for conv in conversations)
        print(f"Projects: {len(projects)}")
        
        # Date range
        timestamps = []
        for conv in conversations:
            if conv.started_at:
                timestamps.append(conv.started_at)
            if conv.ended_at:
                timestamps.append(conv.ended_at)
        
        if timestamps:
            print(f"Date range: {min(timestamps)} to {max(timestamps)}")
    
    if embeddings:
        import numpy as np
        dims = embeddings[0].shape[0] if embeddings else 0
        print(f"Embedding dimensions: {dims}")
        
        # Calculate approximate storage size
        storage_mb = (len(embeddings) * dims * 4) / (1024 * 1024)  # 4 bytes per float32
        print(f"Approximate embedding storage: {storage_mb:.2f} MB")
    
    print("="*60)


def print_database_stats(stats):
    """Print database statistics."""
    print("\n" + "="*60)
    print("📈 DATABASE STATISTICS")
    print("="*60)
    print(f"Conversations: {stats.get('conversation_count', 0)}")
    print(f"Messages: {stats.get('message_count', 0)}")
    print(f"Embedded Messages: {stats.get('embedded_message_count', 0)}")
    print(f"Technical Events: {stats.get('technical_event_count', 0)}")
    print(f"Projects: {stats.get('project_count', 0)}")
    
    earliest = stats.get('earliest_conversation')
    latest = stats.get('latest_conversation')
    if earliest and latest:
        print(f"Date Range: {earliest} to {latest}")
    
    print("="*60)


# Better conversation-to-message mapping
async def ingest_conversations_improved(
    input_path: Path,
    db_config: DatabaseConfig, 
    embedding_config: EmbeddingConfig,
    dry_run: bool = False
):
    """Improved ingestion with proper conversation-to-message mapping."""
    logger.info(f"Starting improved ingestion from {input_path}")
    
    # Initialize database and embedder
    db = ConversationDatabase(db_config) if not dry_run else None
    if db:
        await db.initialize()
    
    try:
        # Process files individually to maintain conversation boundaries
        jsonl_files = list(input_path.rglob("*.jsonl"))
        logger.info(f"Found {len(jsonl_files)} conversation files")
        
        total_conversations = 0
        total_messages = 0
        
        async with OllamaEmbeddings(embedding_config) as embedder:
            # Check model availability
            if not await embedder.is_model_available():
                raise RuntimeError(f"Ollama model {embedding_config.model} not available")
            
            for file_path in jsonl_files:
                try:
                    logger.info(f"Processing {file_path.name}...")
                    
                    # Parse single conversation file
                    from parser import JSONLParser
                    parser = JSONLParser()
                    conversation, messages = parser.parse_conversation_file(file_path)
                    
                    if not messages:
                        logger.warning(f"No messages in {file_path}")
                        continue
                    
                    # Generate embeddings for this conversation
                    message_contents = [msg.content for msg in messages]
                    embeddings = await embedder.embed_conversations(message_contents)
                    
                    logger.info(f"  Conversation: {conversation.project_name}")
                    logger.info(f"  Messages: {len(messages)}")
                    logger.info(f"  Embeddings: {len(embeddings)}")
                    
                    # Store conversation if not dry run
                    if not dry_run and db:
                        await db.store_conversation(conversation, messages, embeddings)
                    
                    total_conversations += 1
                    total_messages += len(messages)
                    
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    continue
        
        if not dry_run and db:
            # Create vector index
            logger.info("Creating vector search index...")
            await db.create_vector_index()
            
            # Print final stats
            stats = await db.get_conversation_stats()
            print_database_stats(stats)
        else:
            print(f"\n✅ Dry run complete: {total_conversations} conversations, {total_messages} messages")
    
    finally:
        if db:
            await db.close()


@click.command()
@click.argument('input_path', type=click.Path(exists=True, path_type=Path))
@click.option('--dry-run', is_flag=True, help='Parse and generate embeddings but do not store in database')
@click.option('--db-host', default='localhost', help='Database host')
@click.option('--db-port', default=5432, help='Database port')
@click.option('--db-name', default='claude_conversations', help='Database name')
@click.option('--db-user', default='claude_user', help='Database user')
@click.option('--db-password', default='claude_pass', help='Database password')
@click.option('--ollama-url', default='http://localhost:11434', help='Ollama API URL')
@click.option('--embedding-model', default='nomic-embed-text', help='Ollama embedding model')
@click.option('--batch-size', default=32, help='Embedding batch size')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
def main(
    input_path: Path,
    dry_run: bool,
    db_host: str,
    db_port: int,
    db_name: str,
    db_user: str,
    db_password: str,
    ollama_url: str,
    embedding_model: str,
    batch_size: int,
    verbose: bool
):
    """
    Ingest Claude conversation files into searchable database.
    
    INPUT_PATH: Directory containing conversation JSONL files (typically ~/.claude/projects/)
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.DEBUG)
    
    # Create configurations
    db_config = DatabaseConfig(
        host=db_host,
        port=db_port,
        database=db_name,
        username=db_user,
        password=db_password
    )
    
    embedding_config = EmbeddingConfig(
        base_url=ollama_url,
        model=embedding_model,
        batch_size=batch_size
    )
    
    # Run ingestion
    try:
        asyncio.run(ingest_conversations_improved(input_path, db_config, embedding_config, dry_run))
    except KeyboardInterrupt:
        logger.info("Ingestion cancelled by user")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()