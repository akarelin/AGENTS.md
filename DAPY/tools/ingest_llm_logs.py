#!/usr/bin/env python3
"""
LLM Log Ingestion Tool for LangSmith

Ingests LLM conversation logs from MD and JSON files into LangSmith datasets.
Supports ChatGPT exports, Claude exports, and custom MD formats.

Usage:
    python ingest_llm_logs.py --source /path/to/logs --dataset my-dataset
    python ingest_llm_logs.py --watch /path/to/logs --dataset my-dataset
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import frontmatter
from langsmith import Client


class LLMLogIngester:
    """Ingest LLM logs from various formats into LangSmith datasets."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize ingester with LangSmith client."""
        self.client = Client(api_key=api_key or os.getenv("LANGCHAIN_API_KEY"))
        
    def ingest_directory(
        self,
        source_dir: str,
        dataset_name: str,
        recursive: bool = True,
        formats: List[str] = None
    ) -> Dict[str, int]:
        """
        Ingest all logs from a directory into a dataset.
        
        Args:
            source_dir: Directory containing log files
            dataset_name: Name of LangSmith dataset
            recursive: Search subdirectories
            formats: File formats to process (default: ['md', 'json'])
            
        Returns:
            Statistics dict with counts
        """
        formats = formats or ['md', 'json']
        stats = {
            'files_processed': 0,
            'conversations_imported': 0,
            'examples_created': 0,
            'errors': 0
        }
        
        # Ensure dataset exists
        try:
            dataset = self.client.read_dataset(dataset_name=dataset_name)
        except:
            dataset = self.client.create_dataset(
                dataset_name=dataset_name,
                description="LLM conversation logs imported from user files"
            )
        
        # Find all log files
        source_path = Path(source_dir)
        pattern = "**/*" if recursive else "*"
        
        for ext in formats:
            for file_path in source_path.glob(f"{pattern}.{ext}"):
                try:
                    print(f"Processing: {file_path}")
                    
                    if ext == 'json':
                        examples = self._parse_json_log(file_path)
                    elif ext == 'md':
                        examples = self._parse_md_log(file_path)
                    else:
                        continue
                    
                    # Add examples to dataset
                    for example in examples:
                        self.client.create_example(
                            dataset_id=dataset.id,
                            inputs=example['inputs'],
                            outputs=example.get('outputs'),
                            metadata=example.get('metadata', {})
                        )
                        stats['examples_created'] += 1
                    
                    stats['files_processed'] += 1
                    stats['conversations_imported'] += len(examples)
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    stats['errors'] += 1
        
        return stats
    
    def _parse_json_log(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse JSON log file (ChatGPT or Claude export format).
        
        Supports:
        - ChatGPT export: conversations.json
        - Claude export: conversations export
        - Custom JSON format
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        examples = []
        
        # Detect format
        if isinstance(data, list):
            # ChatGPT format: list of conversations
            for conversation in data:
                examples.extend(self._parse_chatgpt_conversation(conversation, file_path))
        elif isinstance(data, dict):
            if 'conversations' in data:
                # Claude format: {conversations: [...]}
                for conversation in data['conversations']:
                    examples.extend(self._parse_claude_conversation(conversation, file_path))
            else:
                # Single conversation
                examples.extend(self._parse_generic_conversation(data, file_path))
        
        return examples
    
    def _parse_chatgpt_conversation(
        self,
        conversation: Dict[str, Any],
        source_file: Path
    ) -> List[Dict[str, Any]]:
        """Parse ChatGPT conversation format."""
        examples = []
        
        # Extract metadata
        conv_id = conversation.get('id', 'unknown')
        title = conversation.get('title', 'Untitled')
        create_time = conversation.get('create_time')
        
        # Extract messages
        mapping = conversation.get('mapping', {})
        messages = []
        
        for node_id, node in mapping.items():
            message = node.get('message')
            if message and message.get('content'):
                role = message.get('author', {}).get('role', 'unknown')
                content_parts = message.get('content', {}).get('parts', [])
                content = '\n'.join(str(part) for part in content_parts if part)
                
                if content:
                    messages.append({
                        'role': role,
                        'content': content,
                        'create_time': message.get('create_time')
                    })
        
        # Create examples from message pairs
        for i in range(len(messages) - 1):
            if messages[i]['role'] == 'user' and messages[i+1]['role'] == 'assistant':
                examples.append({
                    'inputs': {
                        'prompt': messages[i]['content']
                    },
                    'outputs': {
                        'response': messages[i+1]['content']
                    },
                    'metadata': {
                        'source': 'chatgpt',
                        'source_file': str(source_file),
                        'conversation_id': conv_id,
                        'conversation_title': title,
                        'create_time': messages[i].get('create_time'),
                        'format': 'chatgpt_export',
                        'annotated': False
                    }
                })
        
        return examples
    
    def _parse_claude_conversation(
        self,
        conversation: Dict[str, Any],
        source_file: Path
    ) -> List[Dict[str, Any]]:
        """Parse Claude conversation format."""
        examples = []
        
        # Extract metadata
        conv_id = conversation.get('uuid', 'unknown')
        name = conversation.get('name', 'Untitled')
        created_at = conversation.get('created_at')
        
        # Extract messages
        messages = conversation.get('chat_messages', [])
        
        # Create examples from message pairs
        for i in range(len(messages) - 1):
            if messages[i].get('sender') == 'human' and messages[i+1].get('sender') == 'assistant':
                examples.append({
                    'inputs': {
                        'prompt': messages[i].get('text', '')
                    },
                    'outputs': {
                        'response': messages[i+1].get('text', '')
                    },
                    'metadata': {
                        'source': 'claude',
                        'source_file': str(source_file),
                        'conversation_id': conv_id,
                        'conversation_name': name,
                        'created_at': created_at,
                        'format': 'claude_export',
                        'annotated': False
                    }
                })
        
        return examples
    
    def _parse_md_log(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse markdown log file.
        
        Supports:
        - Frontmatter metadata
        - Conversation format with headers
        - Daily notes with LLM interactions
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        
        content = post.content
        metadata = post.metadata
        
        examples = []
        
        # Try to extract conversations from markdown
        # Pattern 1: ## User / ## Assistant
        pattern1 = r'##\s*(User|Human|Prompt)[\s:]*\n(.*?)\n##\s*(Assistant|AI|Response)[\s:]*\n(.*?)(?=\n##|\Z)'
        matches = re.finditer(pattern1, content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            user_content = match.group(2).strip()
            assistant_content = match.group(4).strip()
            
            if user_content and assistant_content:
                examples.append({
                    'inputs': {
                        'prompt': user_content
                    },
                    'outputs': {
                        'response': assistant_content
                    },
                    'metadata': {
                        'source': 'markdown',
                        'source_file': str(file_path),
                        'frontmatter': metadata,
                        'format': 'markdown_conversation',
                        'annotated': False
                    }
                })
        
        # Pattern 2: > User: / > Assistant:
        pattern2 = r'>\s*(User|Human):\s*(.*?)\n>\s*(Assistant|AI):\s*(.*?)(?=\n>|\Z)'
        matches = re.finditer(pattern2, content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            user_content = match.group(2).strip()
            assistant_content = match.group(4).strip()
            
            if user_content and assistant_content:
                examples.append({
                    'inputs': {
                        'prompt': user_content
                    },
                    'outputs': {
                        'response': assistant_content
                    },
                    'metadata': {
                        'source': 'markdown',
                        'source_file': str(file_path),
                        'frontmatter': metadata,
                        'format': 'markdown_blockquote',
                        'annotated': False
                    }
                })
        
        return examples
    
    def _parse_generic_conversation(
        self,
        data: Dict[str, Any],
        source_file: Path
    ) -> List[Dict[str, Any]]:
        """Parse generic JSON conversation format."""
        examples = []
        
        # Try to find messages array
        messages = data.get('messages', [])
        
        for i in range(len(messages) - 1):
            msg1 = messages[i]
            msg2 = messages[i+1]
            
            # Check if it's a user/assistant pair
            role1 = msg1.get('role', msg1.get('sender', '')).lower()
            role2 = msg2.get('role', msg2.get('sender', '')).lower()
            
            if role1 in ['user', 'human'] and role2 in ['assistant', 'ai']:
                examples.append({
                    'inputs': {
                        'prompt': msg1.get('content', msg1.get('text', ''))
                    },
                    'outputs': {
                        'response': msg2.get('content', msg2.get('text', ''))
                    },
                    'metadata': {
                        'source': 'generic_json',
                        'source_file': str(source_file),
                        'format': 'generic_conversation',
                        'annotated': False
                    }
                })
        
        return examples


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Ingest LLM logs into LangSmith datasets'
    )
    parser.add_argument(
        '--source',
        required=True,
        help='Source directory containing log files'
    )
    parser.add_argument(
        '--dataset',
        required=True,
        help='LangSmith dataset name'
    )
    parser.add_argument(
        '--recursive',
        action='store_true',
        default=True,
        help='Search subdirectories (default: True)'
    )
    parser.add_argument(
        '--formats',
        nargs='+',
        default=['md', 'json'],
        help='File formats to process (default: md json)'
    )
    parser.add_argument(
        '--api-key',
        help='LangChain API key (or use LANGCHAIN_API_KEY env var)'
    )
    
    args = parser.parse_args()
    
    # Create ingester
    ingester = LLMLogIngester(api_key=args.api_key)
    
    # Ingest logs
    print(f"Ingesting logs from {args.source} into dataset '{args.dataset}'...")
    stats = ingester.ingest_directory(
        source_dir=args.source,
        dataset_name=args.dataset,
        recursive=args.recursive,
        formats=args.formats
    )
    
    # Print results
    print("\nIngestion complete!")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Conversations imported: {stats['conversations_imported']}")
    print(f"Examples created: {stats['examples_created']}")
    print(f"Errors: {stats['errors']}")


if __name__ == '__main__':
    main()
