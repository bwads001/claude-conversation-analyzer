#!/usr/bin/env python3
"""
Test role preservation with a conversation that has 'summary' roles
to verify the database constraint fix worked.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from parser import parse_conversation_files_grouped
from database import ConversationDatabase, DatabaseConfig
from embeddings import OllamaEmbeddings


async def test_summary_role_preservation():
    """Test preservation of 'summary' role specifically."""
    
    config = DatabaseConfig(port=5433)
    db = ConversationDatabase(config)
    embeddings = OllamaEmbeddings()
    
    try:
        await db.initialize()
        
        # Find a conversation with diverse roles for testing
        projects_dir = Path('~/.claude/projects/').expanduser()
        
        print('🧪 SUMMARY ROLE PRESERVATION TEST')
        print('=' * 50)
        print(f'Searching for conversations with diverse roles...')
        
        target_conversation = None
        
        # Search through projects for a conversation with diverse roles
        for project_dir in projects_dir.glob('*'):
            if not project_dir.is_dir() or not list(project_dir.glob('*.jsonl')):
                continue
                
            grouped_conversations = parse_conversation_files_grouped(project_dir)
            
            for conv_meta, messages in grouped_conversations:
                roles = set(msg.role for msg in messages)
                # Look for conversations with non-standard roles
                if len(roles) > 2 and any(role not in ['user', 'assistant', 'system'] for role in roles):
                    target_conversation = (conv_meta, messages)
                    print(f'Found test conversation with roles: {sorted(roles)}')
                    break
            
            if target_conversation:
                break
        
        if not target_conversation:
            print('❌ No conversations with diverse roles found for testing')
            # Fall back to any conversation
            for project_dir in projects_dir.glob('*'):
                if project_dir.is_dir() and list(project_dir.glob('*.jsonl')):
                    grouped_conversations = parse_conversation_files_grouped(project_dir)
                    if grouped_conversations:
                        target_conversation = grouped_conversations[0]
                        conv_meta, messages = target_conversation
                        print(f'Using fallback conversation with {len(set(msg.role for msg in messages))} role types')
                        break
            
            if not target_conversation:
                print('❌ No conversations found for testing')
                return False
        
        conv_meta, messages = target_conversation
        
        print(f'Found conversation: {conv_meta.session_id[:8]}...')
        print(f'Total messages: {len(messages)}')
        
        # Analyze roles before storage
        original_roles = set(msg.role for msg in messages)
        role_counts = {}
        for msg in messages:
            role_counts[msg.role] = role_counts.get(msg.role, 0) + 1
        
        print(f'Original roles: {sorted(original_roles)}')
        print('Original role counts:')
        for role in sorted(role_counts.keys()):
            print(f'  {role}: {role_counts[role]} messages')
        print()
        
        # Generate embeddings for substantial content only
        substantial = [m for m in messages if len(m.content.strip()) > 10]
        print(f'Messages with substantial content: {len(substantial)}')
        
        if substantial:
            contents = [m.content for m in substantial]
            print('Generating embeddings...')
            embedding_vectors = await embeddings.embed_conversations(contents)
            embedding_dict = {m.uuid: emb for m, emb in zip(substantial, embedding_vectors)}
            full_embeddings = [embedding_dict.get(m.uuid) for m in messages]
        else:
            full_embeddings = [None] * len(messages)
        
        # Store in database
        print('Storing conversation in database...')
        conversation_id = await db.store_conversation(conv_meta, messages, full_embeddings)
        print(f'✅ Stored as conversation: {conversation_id}')
        print()
        
        # Verify what was stored
        print('📊 VERIFICATION: Original vs Stored')
        print('-' * 40)
        
        async with db.get_connection() as conn:
            stored_roles = await conn.fetch('''
                SELECT role, COUNT(*) as count 
                FROM messages 
                WHERE conversation_id = $1 
                GROUP BY role 
                ORDER BY role
            ''', conversation_id)
            
            stored_role_names = set(row['role'] for row in stored_roles)
            
            print(f'Original roles: {sorted(original_roles)}')
            print(f'Stored roles:   {sorted(stored_role_names)}')
            print()
            
            print('Stored role counts:')
            for row in stored_roles:
                print(f'  {row["role"]}: {row["count"]} messages')
            
            # Critical test: Is 'summary' role preserved?
            if 'summary' in stored_role_names:
                print('\\n✅ SUCCESS: summary role preserved!')
                success = True
            else:
                print('\\n❌ FAILURE: summary role was lost/corrupted!')
                success = False
            
            # Overall test
            if original_roles == stored_role_names:
                print('✅ SUCCESS: All original roles preserved exactly!')
                return True
            else:
                missing = original_roles - stored_role_names
                extra = stored_role_names - original_roles
                print(f'\\n❌ FAILURE: Role mismatch!')
                if missing:
                    print(f'  Missing from DB: {sorted(missing)}')
                if extra:
                    print(f'  Extra in DB: {sorted(extra)}')
                return False
        
    except Exception as e:
        print(f'❌ ERROR: {e}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        await db.close()
        await embeddings.close()


if __name__ == '__main__':
    result = asyncio.run(test_summary_role_preservation())
    sys.exit(0 if result else 1)