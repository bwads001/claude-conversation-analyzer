#!/usr/bin/env python3
"""
Database initialization script for Claude Conversation Analyzer.

Creates database schema and runs initial setup.
"""

import asyncio
import sys
from pathlib import Path
import click

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import ConversationDatabase, DatabaseConfig


async def initialize_database(db_config: DatabaseConfig):
    """Initialize the database schema."""
    print("🗄️  Initializing Claude Conversation Analyzer database...")
    
    db = ConversationDatabase(db_config)
    
    try:
        await db.initialize()
        
        # Create database schema
        print("📋 Creating database schema...")
        await db.create_schema()
        
        # Test the connection and show stats
        stats = await db.get_conversation_stats()
        print("✅ Database initialized successfully!")
        print(f"📊 Current stats: {stats}")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise
    finally:
        await db.close()


@click.command()
@click.option('--db-host', default='localhost', help='Database host')
@click.option('--db-port', default=5432, help='Database port')
@click.option('--db-name', default='claude_conversations', help='Database name')
@click.option('--db-user', default='claude_user', help='Database user')
@click.option('--db-password', default='claude_pass', help='Database password')
def main(
    db_host: str,
    db_port: int,
    db_name: str,
    db_user: str,
    db_password: str
):
    """Initialize the Claude Conversation Analyzer database."""
    db_config = DatabaseConfig(
        host=db_host,
        port=db_port,
        database=db_name,
        username=db_user,
        password=db_password
    )
    
    try:
        asyncio.run(initialize_database(db_config))
    except Exception as e:
        print(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()