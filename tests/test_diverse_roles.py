#!/usr/bin/env python3
"""
Test script to find and test conversations with diverse role types
(summary, tool_result, etc.) to verify role preservation.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from parser import parse_conversation_files_grouped


async def find_diverse_roles():
    """Find conversations with non-standard roles to test preservation."""
    
    print('🔍 SEARCHING FOR DIVERSE ROLE TYPES')
    print('=' * 50)
    
    # Check sample conversation directory for diverse roles
    projects_dir = Path('~/.claude/projects/').expanduser()
    
    if not projects_dir.exists():
        print(f'❌ Path not found: {projects_dir}')
        return
    
    # Find a project directory with conversation files
    sample_project = None
    for project_dir in projects_dir.glob('*'):
        if project_dir.is_dir() and list(project_dir.glob('*.jsonl')):
            sample_project = project_dir
            break
    
    if not sample_project:
        print('❌ No project directories with conversation files found')
        return
        
    grouped_conversations = parse_conversation_files_grouped(sample_project)
    print(f'Analyzing {len(grouped_conversations)} conversations...')
    print()
    
    all_roles = set()
    interesting_conversations = []
    
    for i, (conv_meta, messages) in enumerate(grouped_conversations[:10]):  # First 10 only
        conv_roles = set(msg.role for msg in messages)
        all_roles.update(conv_roles)
        
        # Look for non-standard roles
        non_standard = conv_roles - {'user', 'assistant', 'system'}
        if non_standard:
            interesting_conversations.append((conv_meta, messages, conv_roles))
            print(f'📂 Conversation {i+1}: {conv_meta.session_id[:8]}...')
            print(f'   Roles: {sorted(conv_roles)}')
            print(f'   Non-standard: {sorted(non_standard)} ⭐')
            print(f'   Messages: {len(messages)}')
            print()
    
    print(f'📊 SUMMARY:')
    print(f'   All unique roles found: {sorted(all_roles)}')
    print(f'   Standard roles: {sorted(all_roles & {"user", "assistant", "system"})}')
    print(f'   Non-standard roles: {sorted(all_roles - {"user", "assistant", "system"})}')
    print(f'   Conversations with diverse roles: {len(interesting_conversations)}')
    
    if interesting_conversations:
        print(f'\n🎯 BEST TEST CANDIDATE:')
        best_conv = interesting_conversations[0]
        conv_meta, messages, roles = best_conv
        print(f'   Session ID: {conv_meta.session_id}')
        print(f'   File: {conv_meta.file_path}')
        print(f'   Roles: {sorted(roles)}')
        print(f'   Messages: {len(messages)}')
        
        return conv_meta.session_id
    else:
        print('\n📭 No conversations with non-standard roles found in first 10.')
        return None


if __name__ == '__main__':
    asyncio.run(find_diverse_roles())