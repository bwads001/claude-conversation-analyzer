#!/usr/bin/env python3
"""
Command-line search interface for Claude Conversation Analyzer.

Provides semantic search capabilities over stored conversation history.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import click

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import ConversationDatabase, DatabaseConfig
from embeddings import OllamaEmbeddings, EmbeddingConfig

# Color formatting for CLI output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def format_result(result: dict, index: int) -> str:
    """Format a search result for display."""
    content = result['content']
    
    # Truncate very long content
    if len(content) > 300:
        content = content[:300] + "..."
    
    # Format timestamp
    timestamp = result['timestamp']
    if timestamp:
        time_str = timestamp.strftime("%Y-%m-%d %H:%M")
    else:
        time_str = "Unknown time"
    
    # Similarity score as percentage
    similarity_pct = (1 - result['similarity']) * 100
    
    return f"""
{Colors.BOLD}[{index + 1}] {Colors.OKBLUE}{result['project_name']}{Colors.ENDC} {Colors.OKCYAN}({similarity_pct:.1f}% match){Colors.ENDC}
{Colors.OKGREEN}📅 {time_str}{Colors.ENDC} | {Colors.WARNING}👤 {result['role']}{Colors.ENDC}
{content}
{Colors.HEADER}📁 {result.get('git_branch', 'No branch')}{Colors.ENDC}
""".strip()


async def search_conversations(
    query: str,
    db_config: DatabaseConfig,
    embedding_config: EmbeddingConfig,
    limit: int = 10,
    similarity_threshold: float = 0.7,
    project_filter: Optional[str] = None,
    date_after: Optional[datetime] = None,
    date_before: Optional[datetime] = None,
    similar_to_text: Optional[str] = None
):
    """
    Search conversations using semantic similarity.
    
    Args:
        query: Search query text
        db_config: Database configuration
        embedding_config: Embedding configuration  
        limit: Maximum results to return
        similarity_threshold: Similarity threshold (0-1, lower = more similar)
        project_filter: Filter by project name
        date_after: Filter conversations after this date
        date_before: Filter conversations before this date
        similar_to_text: Find conversations similar to this specific text
    """
    # Use similar_to_text if provided, otherwise use query
    search_text = similar_to_text or query
    
    print(f"{Colors.BOLD}🔍 Searching for: {Colors.OKCYAN}{search_text}{Colors.ENDC}")
    
    if project_filter:
        print(f"{Colors.OKGREEN}📁 Project filter: {project_filter}{Colors.ENDC}")
    
    if date_after or date_before:
        date_range = []
        if date_after:
            date_range.append(f"after {date_after.strftime('%Y-%m-%d')}")
        if date_before:
            date_range.append(f"before {date_before.strftime('%Y-%m-%d')}")
        print(f"{Colors.WARNING}📅 Date filter: {' and '.join(date_range)}{Colors.ENDC}")
    
    print()
    
    # Generate query embedding
    async with OllamaEmbeddings(embedding_config) as embedder:
        if not await embedder.is_model_available():
            print(f"{Colors.FAIL}❌ Embedding model {embedding_config.model} not available{Colors.ENDC}")
            return
        
        print(f"{Colors.OKCYAN}🤖 Generating query embedding...{Colors.ENDC}")
        query_embedding = await embedder.embed_single(search_text)
    
    # Search database
    db = ConversationDatabase(db_config)
    await db.initialize()
    
    try:
        results = await db.search_similar(
            query_embedding,
            limit=limit,
            similarity_threshold=similarity_threshold,
            project_filter=project_filter,
            date_after=date_after,
            date_before=date_before
        )
        
        if not results:
            print(f"{Colors.WARNING}🤷 No similar conversations found{Colors.ENDC}")
            print(f"{Colors.HEADER}💡 Try:{Colors.ENDC}")
            print("  • Using different keywords")
            print("  • Increasing similarity threshold with --threshold")
            print("  • Removing date/project filters")
            return
        
        print(f"{Colors.BOLD}📋 Found {len(results)} similar conversations:{Colors.ENDC}\n")
        
        for i, result in enumerate(results):
            print(format_result(result, i))
            print("-" * 80)
    
    finally:
        await db.close()


async def show_database_stats(db_config: DatabaseConfig):
    """Show database statistics."""
    db = ConversationDatabase(db_config)
    await db.initialize()
    
    try:
        stats = await db.get_conversation_stats()
        projects = await db.get_projects()
        
        print(f"{Colors.BOLD}📊 DATABASE STATISTICS{Colors.ENDC}")
        print("=" * 50)
        print(f"{Colors.OKGREEN}Conversations:{Colors.ENDC} {stats.get('conversation_count', 0)}")
        print(f"{Colors.OKGREEN}Messages:{Colors.ENDC} {stats.get('message_count', 0)}")
        print(f"{Colors.OKGREEN}Embedded Messages:{Colors.ENDC} {stats.get('embedded_message_count', 0)}")
        print(f"{Colors.OKGREEN}Technical Events:{Colors.ENDC} {stats.get('technical_event_count', 0)}")
        print(f"{Colors.OKGREEN}Projects:{Colors.ENDC} {stats.get('project_count', 0)}")
        
        earliest = stats.get('earliest_conversation')
        latest = stats.get('latest_conversation')
        if earliest and latest:
            print(f"{Colors.OKGREEN}Date Range:{Colors.ENDC} {earliest} to {latest}")
        
        if projects:
            print(f"\n{Colors.BOLD}📁 PROJECTS:{Colors.ENDC}")
            for project in projects[:10]:  # Show top 10
                name = project['project_name'][:40]
                count = project['conversation_count']
                latest_date = project['latest_conversation']
                if latest_date:
                    date_str = latest_date.strftime("%Y-%m-%d")
                else:
                    date_str = "Unknown"
                print(f"  {Colors.OKCYAN}{name:<40}{Colors.ENDC} {count:>3} conversations (latest: {date_str})")
            
            if len(projects) > 10:
                print(f"  ... and {len(projects) - 10} more projects")
    
    finally:
        await db.close()


@click.command()
@click.argument('query', required=False)
@click.option('--limit', '-l', default=10, help='Maximum number of results')
@click.option('--threshold', '-t', default=0.7, help='Similarity threshold (0-1, lower = more similar)')
@click.option('--project', '-p', help='Filter by project name')
@click.option('--after', help='Filter conversations after date (YYYY-MM-DD)')
@click.option('--before', help='Filter conversations before date (YYYY-MM-DD)')
@click.option('--similar-to', help='Find conversations similar to specific text')
@click.option('--stats', is_flag=True, help='Show database statistics')
@click.option('--db-host', default='localhost', help='Database host')
@click.option('--db-port', default=5432, help='Database port')
@click.option('--db-name', default='claude_conversations', help='Database name')
@click.option('--db-user', default='claude_user', help='Database user')
@click.option('--db-password', default='claude_pass', help='Database password')
@click.option('--ollama-url', default='http://localhost:11434', help='Ollama API URL')
@click.option('--embedding-model', default='nomic-embed-text', help='Ollama embedding model')
def main(
    query: Optional[str],
    limit: int,
    threshold: float,
    project: Optional[str],
    after: Optional[str],
    before: Optional[str],
    similar_to: Optional[str],
    stats: bool,
    db_host: str,
    db_port: int,
    db_name: str,
    db_user: str,
    db_password: str,
    ollama_url: str,
    embedding_model: str
):
    """
    Search Claude conversation history using semantic similarity.
    
    Examples:
      search_cli.py "database performance optimization"
      search_cli.py "AWS deployment" --project "MyProject" 
      search_cli.py "error handling" --after "2025-08-01"
      search_cli.py --similar-to "ImportError: No module named pandas"
      search_cli.py --stats
    """
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
        model=embedding_model
    )
    
    # Parse date filters
    date_after = None
    date_before = None
    
    if after:
        try:
            date_after = datetime.strptime(after, "%Y-%m-%d")
        except ValueError:
            click.echo(f"Invalid date format for --after: {after}. Use YYYY-MM-DD")
            return
    
    if before:
        try:
            date_before = datetime.strptime(before, "%Y-%m-%d")
        except ValueError:
            click.echo(f"Invalid date format for --before: {before}. Use YYYY-MM-DD")
            return
    
    # Run search or show stats
    try:
        if stats:
            asyncio.run(show_database_stats(db_config))
        elif query or similar_to:
            search_query = query or "similar content"  # Placeholder when using --similar-to
            asyncio.run(search_conversations(
                search_query,
                db_config,
                embedding_config,
                limit=limit,
                similarity_threshold=threshold,
                project_filter=project,
                date_after=date_after,
                date_before=date_before,
                similar_to_text=similar_to
            ))
        else:
            print(f"{Colors.FAIL}❌ Please provide a query or use --stats{Colors.ENDC}")
            print(f"{Colors.HEADER}Examples:{Colors.ENDC}")
            print('  search_cli.py "database optimization"')
            print('  search_cli.py "error handling" --project "MyProject"')
            print('  search_cli.py --similar-to "ImportError: module not found"')
            print('  search_cli.py --stats')
    
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Search cancelled by user{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}❌ Search failed: {e}{Colors.ENDC}")
        sys.exit(1)


if __name__ == "__main__":
    main()