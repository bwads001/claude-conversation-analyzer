#!/usr/bin/env python3
"""
Flexible ingestion script for Claude conversation files.

Supports multiple ways to specify what to ingest:
- All projects: python ingest_flexible.py --all
- By project name: python ingest_flexible.py --project "wo-25-container-poc"
- By full path: python ingest_flexible.py --project-path "/path/to/conversations"
- Single file: python ingest_flexible.py --file "/path/to/conversation.jsonl"
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from parser import parse_conversation_files_grouped
from database import ConversationDatabase, DatabaseConfig
from embeddings import OllamaEmbeddings


def find_projects_by_name(project_name: str, claude_projects_dir: Path, allow_multiple: bool = True) -> list[Path]:
    """Find project directories by matching the project name."""
    
    # Look for directories that contain the project name
    candidates = []
    for project_dir in claude_projects_dir.glob('*'):
        if not project_dir.is_dir():
            continue
            
        # Only include directories with conversation files
        if not list(project_dir.glob('*.jsonl')):
            continue
            
        dir_name = project_dir.name.lower()
        search_name = project_name.lower()
        
        # Match if project name is contained in directory name
        if search_name in dir_name:
            candidates.append(project_dir)
    
    if not candidates:
        raise ValueError(f"No project found matching '{project_name}' in {claude_projects_dir}")
    
    if len(candidates) == 1 or allow_multiple:
        if len(candidates) > 1:
            print(f"Found {len(candidates)} projects matching '{project_name}':")
            total_files = 0
            for candidate in candidates:
                jsonl_count = len(list(candidate.glob('*.jsonl')))
                total_files += jsonl_count
                print(f"  📂 {candidate.name} ({jsonl_count} files)")
            print(f"Total: {total_files} conversation files")
            print()
        return candidates
    
    # Multiple matches but not allowing multiple - show them and ask user to be more specific
    print(f"Multiple projects found matching '{project_name}':")
    for i, candidate in enumerate(candidates, 1):
        jsonl_count = len(list(candidate.glob('*.jsonl')))
        print(f"  {i}. {candidate.name} ({jsonl_count} files)")
    
    raise ValueError(f"Multiple matches found. Use --project-multiple to ingest all, or be more specific")


def list_available_projects(claude_projects_dir: Path) -> None:
    """List all available projects with conversation files."""
    
    print(f"📂 Available projects in {claude_projects_dir}:")
    print("=" * 60)
    
    projects_with_files = []
    for project_dir in sorted(claude_projects_dir.glob('*')):
        if not project_dir.is_dir():
            continue
        
        jsonl_files = list(project_dir.glob('*.jsonl'))
        if jsonl_files:
            # Extract meaningful project name from directory
            dir_name = project_dir.name
            # Remove common prefixes to make it cleaner
            clean_name = dir_name.replace('-home-bwadsworth-', '')
            projects_with_files.append((clean_name, dir_name, len(jsonl_files)))
    
    if not projects_with_files:
        print("  No projects with conversation files found.")
        return
    
    for clean_name, full_name, file_count in projects_with_files:
        print(f"  📝 {clean_name}")
        print(f"     Full name: {full_name}")
        print(f"     Files: {file_count}")
        print()
    
    print("Usage examples:")
    print(f"  python {sys.argv[0]} --project 'work'")
    print(f"  python {sys.argv[0]} --project 'my-project'")
    print(f"  python {sys.argv[0]} --project-path '{claude_projects_dir}/specific-project'")


async def ingest_conversations(project_paths: list, db_config: DatabaseConfig) -> bool:
    """Ingest conversations from the given project paths."""
    
    db = ConversationDatabase(db_config)
    embeddings = OllamaEmbeddings()
    
    try:
        await db.initialize()
        
        total_conversations = 0
        total_messages = 0
        total_embedded = 0
        
        for i, project_path in enumerate(project_paths, 1):
            print(f"\n[{i}/{len(project_paths)}] Processing: {project_path.name}")
            print("=" * 60)
            
            try:
                # Check for conversation files
                jsonl_files = list(project_path.glob('*.jsonl'))
                if not jsonl_files:
                    print(f"  ⚠️  No .jsonl files found, skipping")
                    continue
                
                print(f"  📄 Found {len(jsonl_files)} conversation files")
                
                # Parse conversations
                grouped_conversations = parse_conversation_files_grouped(project_path)
                print(f"  📝 Parsed {len(grouped_conversations)} conversations")
                
                project_messages = 0
                project_embedded = 0
                
                for j, (conv_meta, messages) in enumerate(grouped_conversations, 1):
                    print(f"    [{j}/{len(grouped_conversations)}] {conv_meta.session_id[:8]}... ({len(messages)} messages)")
                    
                    # Generate embeddings for substantial content
                    substantial = [m for m in messages if len(m.content.strip()) > 10]
                    if substantial:
                        contents = [m.content for m in substantial]
                        embedding_vectors = await embeddings.embed_conversations(contents)
                        embedding_dict = {m.uuid: emb for m, emb in zip(substantial, embedding_vectors)}
                        full_embeddings = [embedding_dict.get(m.uuid) for m in messages]
                        project_embedded += len(substantial)
                    else:
                        full_embeddings = [None] * len(messages)
                    
                    # Store in database
                    try:
                        conversation_id = await db.store_conversation(conv_meta, messages, full_embeddings)
                        project_messages += len(messages)
                        print(f"      ✅ Stored: {conversation_id}")
                    except Exception as e:
                        if 'duplicate key' in str(e).lower():
                            print(f"      ⚠️  Skipped (already exists)")
                        else:
                            print(f"      ❌ Failed: {str(e)[:100]}...")
                
                total_conversations += len(grouped_conversations)
                total_messages += project_messages
                total_embedded += project_embedded
                
                print(f"  📊 Project totals: {len(grouped_conversations)} conversations, {project_messages} messages, {project_embedded} embedded")
                
            except Exception as e:
                print(f"  ❌ Project failed: {e}")
                continue
        
        print(f"\n🎉 INGESTION COMPLETE!")
        print("=" * 30)
        print(f"Total conversations: {total_conversations}")
        print(f"Total messages: {total_messages}")
        print(f"Total embedded: {total_embedded}")
        
        # Final database statistics
        stats = await db.get_conversation_stats()
        print(f"\nDatabase statistics:")
        print(f"  Conversations: {stats.get('conversation_count', 0)}")
        print(f"  Messages: {stats.get('message_count', 0)}")
        print(f"  Embedded messages: {stats.get('embedded_message_count', 0)}")
        print(f"  Projects: {stats.get('project_count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ INGESTION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await db.close()
        await embeddings.close()


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Claude conversation files into the analyzer database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                           # Ingest all projects
  %(prog)s --project "my-project"          # Ingest single project matching "my-project" (fails if multiple)
  %(prog)s --project-multiple "work"       # Ingest ALL projects matching "work"
  %(prog)s --project-multiple "mycode"     # Ingest all mycode/project1, mycode/project2, etc.
  %(prog)s --project-path "/path/to/proj"  # Ingest specific directory
  %(prog)s --file "conversation.jsonl"     # Ingest single file
  %(prog)s --list                          # List available projects
        """
    )
    
    # Mutually exclusive group for input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--all', action='store_true',
                            help='Ingest all projects in ~/.claude/projects/')
    input_group.add_argument('--project', type=str,
                            help='Project name to search for (partial matching)')
    input_group.add_argument('--project-multiple', type=str,
                            help='Project name to search for - ingest ALL matching projects')
    input_group.add_argument('--project-path', type=Path,
                            help='Full path to project directory')
    input_group.add_argument('--file', type=Path,
                            help='Single conversation file to ingest')
    input_group.add_argument('--list', action='store_true',
                            help='List available projects')
    
    # Database connection options
    parser.add_argument('--db-host', default='localhost', help='Database host')
    parser.add_argument('--db-port', type=int, default=5433, help='Database port')
    parser.add_argument('--db-name', default='claude_conversations', help='Database name')
    parser.add_argument('--db-user', default='claude_user', help='Database user')
    parser.add_argument('--db-password', default='claude_pass', help='Database password')
    
    # Claude projects directory
    parser.add_argument('--claude-projects-dir', type=Path, 
                       default=Path('~/.claude/projects/').expanduser(),
                       help='Path to Claude projects directory')
    
    args = parser.parse_args()
    
    # Create database config
    db_config = DatabaseConfig(
        host=args.db_host,
        port=args.db_port,
        database=args.db_name,
        username=args.db_user,
        password=args.db_password
    )
    
    # Handle list option
    if args.list:
        list_available_projects(args.claude_projects_dir)
        return
    
    # Determine project paths to ingest
    project_paths = []
    
    try:
        if args.all:
            # Find all projects with conversation files
            for project_dir in args.claude_projects_dir.glob('*'):
                if project_dir.is_dir() and list(project_dir.glob('*.jsonl')):
                    project_paths.append(project_dir)
            
            if not project_paths:
                print(f"No projects with conversation files found in {args.claude_projects_dir}")
                return
                
            print(f"Found {len(project_paths)} projects to ingest")
            
        elif args.project:
            # Find single project by name (strict matching)
            project_matches = find_projects_by_name(args.project, args.claude_projects_dir, allow_multiple=False)
            project_paths.extend(project_matches)
            
        elif args.project_multiple:
            # Find multiple projects by name (allow multiple matches)
            project_matches = find_projects_by_name(args.project_multiple, args.claude_projects_dir, allow_multiple=True)
            project_paths.extend(project_matches)
            
        elif args.project_path:
            # Use specified path
            if not args.project_path.exists():
                print(f"Project path does not exist: {args.project_path}")
                return
            project_paths.append(args.project_path)
            
        elif args.file:
            # Single file - create temporary directory structure
            if not args.file.exists():
                print(f"File does not exist: {args.file}")
                return
            project_paths.append(args.file.parent)
        
        # Run ingestion
        result = asyncio.run(ingest_conversations(project_paths, db_config))
        sys.exit(0 if result else 1)
        
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nIngestion cancelled by user")
        sys.exit(1)


if __name__ == '__main__':
    main()