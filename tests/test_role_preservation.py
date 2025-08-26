#!/usr/bin/env python3
"""
Test script to verify that original Claude conversation roles are preserved
during parsing and database storage (no role normalization/corruption).
"""

import sys
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from parser import parse_conversation_files_grouped
from database import ConversationDatabase, DatabaseConfig
from embeddings import OllamaEmbeddings


async def test_role_preservation():
    """Test that original roles from Claude conversations are preserved exactly."""
    
    config = DatabaseConfig(port=5433)
    db = ConversationDatabase(config)
    embeddings = OllamaEmbeddings()
    
    try:
        await db.initialize()
        
        # Test with small sample project
        test_path = Path('~/.claude/projects/').expanduser().glob('*').__next__()
        grouped_conversations = parse_conversation_files_grouped(test_path)
        
        print('🧪 ROLE PRESERVATION TEST')
        print('=' * 50)
        print(f'Test project: {test_path.name}')
        print(f'Conversations found: {len(grouped_conversations)}')
        print()
        
        # Analyze roles BEFORE database storage
        original_roles = set()
        total_messages = 0
        
        for conv_meta, messages in grouped_conversations:
            print(f'Conversation: {conv_meta.session_id[:8]}...')
            print(f'  Total messages: {len(messages)}')
            
            # Collect all original roles
            conv_roles = set(msg.role for msg in messages)
            original_roles.update(conv_roles)
            total_messages += len(messages)
            
            print(f'  Original roles in this conversation: {sorted(conv_roles)}')
            
            # Generate embeddings for substantial content
            substantial = [m for m in messages if len(m.content.strip()) > 10]
            if substantial:
                contents = [m.content for m in substantial]
                embedding_vectors = await embeddings.embed_conversations(contents)
                embedding_dict = {m.uuid: emb for m, emb in zip(substantial, embedding_vectors)}
                full_embeddings = [embedding_dict.get(m.uuid) for m in messages]
            else:
                full_embeddings = [None] * len(messages)
            
            # Store in database
            conversation_id = await db.store_conversation(conv_meta, messages, full_embeddings)
            print(f'  ✅ Stored as conversation: {conversation_id}')
            print()
        
        # Verify what was actually stored in database
        print('📊 VERIFICATION: Database vs Original')
        print('-' * 30)
        
        async with db.get_connection() as conn:
            stored_roles = await conn.fetch(
                'SELECT role, COUNT(*) as count FROM messages GROUP BY role ORDER BY role'
            )
            stored_role_names = set(row['role'] for row in stored_roles)
            
            print(f'Original roles found: {sorted(original_roles)}')
            print(f'Stored roles in DB:   {sorted(stored_role_names)}')
            print()
            
            print('Detailed breakdown:')
            for row in stored_roles:
                print(f'  {row["role"]}: {row["count"]} messages')
            
            # Test result
            if original_roles == stored_role_names:
                print('\n✅ SUCCESS: All original roles preserved!')
                return True
            else:
                missing = original_roles - stored_role_names
                extra = stored_role_names - original_roles
                print(f'\n❌ FAILURE: Role mismatch!')
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
    result = asyncio.run(test_role_preservation())
    sys.exit(0 if result else 1)