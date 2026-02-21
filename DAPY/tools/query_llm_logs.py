#!/usr/bin/env python3
"""
LLM Log Query Tool for Test Case Generation

Query ingested LLM logs in LangSmith to generate test cases automatically.
Supports filtering, pattern detection, and test case extraction.

Usage:
    python query_llm_logs.py --dataset my-dataset --query "git operations"
    python query_llm_logs.py --dataset my-dataset --generate-tests --output tests.json
"""

import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langsmith import Client
from openai import OpenAI


class LLMLogQuerier:
    """Query LLM logs and generate test cases."""
    
    def __init__(
        self,
        langsmith_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """Initialize querier with LangSmith and OpenAI clients."""
        self.ls_client = Client(
            api_key=langsmith_api_key or os.getenv("LANGCHAIN_API_KEY")
        )
        self.openai_client = OpenAI(
            api_key=openai_api_key or os.getenv("OPENAI_API_KEY")
        )
    
    def query_examples(
        self,
        dataset_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Query examples from dataset with filters.
        
        Args:
            dataset_name: Name of LangSmith dataset
            filters: Filter criteria (metadata fields)
            limit: Maximum number of examples to return
            
        Returns:
            List of matching examples
        """
        dataset = self.ls_client.read_dataset(dataset_name=dataset_name)
        examples = list(self.ls_client.list_examples(dataset_id=dataset.id))
        
        # Apply filters
        if filters:
            examples = [
                ex for ex in examples
                if self._matches_filters(ex, filters)
            ]
        
        # Apply limit
        if limit:
            examples = examples[:limit]
        
        return examples
    
    def _matches_filters(
        self,
        example: Any,
        filters: Dict[str, Any]
    ) -> bool:
        """Check if example matches filter criteria."""
        metadata = getattr(example, 'metadata', {}) or {}
        
        for key, value in filters.items():
            if key not in metadata:
                return False
            
            if isinstance(value, list):
                # Match any value in list
                if metadata[key] not in value:
                    return False
            elif isinstance(value, str):
                # Substring match
                if value.lower() not in str(metadata[key]).lower():
                    return False
            else:
                # Exact match
                if metadata[key] != value:
                    return False
        
        return True
    
    def search_by_keyword(
        self,
        dataset_name: str,
        keyword: str,
        search_in: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search examples by keyword in prompts or responses.
        
        Args:
            dataset_name: Name of LangSmith dataset
            keyword: Keyword to search for
            search_in: Fields to search ('prompt', 'response', 'both')
            
        Returns:
            List of matching examples
        """
        search_in = search_in or ['both']
        examples = self.query_examples(dataset_name)
        
        matches = []
        for ex in examples:
            inputs = getattr(ex, 'inputs', {}) or {}
            outputs = getattr(ex, 'outputs', {}) or {}
            
            prompt = inputs.get('prompt', '')
            response = outputs.get('response', '')
            
            keyword_lower = keyword.lower()
            
            if 'prompt' in search_in or 'both' in search_in:
                if keyword_lower in prompt.lower():
                    matches.append(ex)
                    continue
            
            if 'response' in search_in or 'both' in search_in:
                if keyword_lower in response.lower():
                    matches.append(ex)
        
        return matches
    
    def detect_patterns(
        self,
        dataset_name: str,
        min_frequency: int = 3
    ) -> Dict[str, List[str]]:
        """
        Detect common patterns in prompts.
        
        Args:
            dataset_name: Name of LangSmith dataset
            min_frequency: Minimum occurrences to be considered a pattern
            
        Returns:
            Dict of pattern types and examples
        """
        examples = self.query_examples(dataset_name)
        
        patterns = {
            'commands': Counter(),
            'questions': Counter(),
            'requests': Counter(),
            'topics': Counter()
        }
        
        for ex in examples:
            inputs = getattr(ex, 'inputs', {}) or {}
            prompt = inputs.get('prompt', '')
            
            # Detect commands (short, imperative)
            if len(prompt.split()) <= 5:
                patterns['commands'][prompt.lower()] += 1
            
            # Detect questions
            if '?' in prompt:
                patterns['questions'][prompt[:100]] += 1
            
            # Detect requests (starts with action verbs)
            action_verbs = ['create', 'update', 'delete', 'show', 'list', 'get', 'find', 'search']
            first_word = prompt.split()[0].lower() if prompt.split() else ''
            if first_word in action_verbs:
                patterns['requests'][prompt[:100]] += 1
            
            # Detect topics (extract key phrases)
            # Simple: look for capitalized phrases
            topics = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', prompt)
            for topic in topics:
                patterns['topics'][topic] += 1
        
        # Filter by frequency
        result = {}
        for pattern_type, counter in patterns.items():
            result[pattern_type] = [
                item for item, count in counter.most_common()
                if count >= min_frequency
            ]
        
        return result
    
    def generate_test_cases(
        self,
        dataset_name: str,
        num_tests: int = 10,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate test cases from examples using AI.
        
        Args:
            dataset_name: Name of LangSmith dataset
            num_tests: Number of test cases to generate
            criteria: Selection criteria (e.g., {'annotated': True})
            
        Returns:
            List of test cases
        """
        # Get examples
        filters = criteria or {}
        examples = self.query_examples(dataset_name, filters=filters)
        
        if not examples:
            print("No examples found matching criteria")
            return []
        
        # Analyze patterns
        patterns = self.detect_patterns(dataset_name)
        
        # Use AI to generate test cases
        prompt = self._build_test_generation_prompt(examples, patterns, num_tests)
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a test case generation expert. Generate comprehensive test cases from real user interactions."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7
        )
        
        # Parse response
        test_cases_text = response.choices[0].message.content
        test_cases = self._parse_test_cases(test_cases_text)
        
        return test_cases[:num_tests]
    
    def _build_test_generation_prompt(
        self,
        examples: List[Any],
        patterns: Dict[str, List[str]],
        num_tests: int
    ) -> str:
        """Build prompt for AI test case generation."""
        # Sample examples
        sample_size = min(20, len(examples))
        sample_examples = examples[:sample_size]
        
        prompt = f"""Generate {num_tests} test cases based on these real user interactions.

PATTERNS DETECTED:
Commands: {', '.join(patterns.get('commands', [])[:10])}
Questions: {', '.join(patterns.get('questions', [])[:5])}
Requests: {', '.join(patterns.get('requests', [])[:5])}
Topics: {', '.join(patterns.get('topics', [])[:10])}

SAMPLE INTERACTIONS:
"""
        
        for i, ex in enumerate(sample_examples, 1):
            inputs = getattr(ex, 'inputs', {}) or {}
            outputs = getattr(ex, 'outputs', {}) or {}
            metadata = getattr(ex, 'metadata', {}) or {}
            
            prompt += f"\n{i}. User: {inputs.get('prompt', '')[:200]}\n"
            prompt += f"   Assistant: {outputs.get('response', '')[:200]}\n"
            if metadata.get('annotated'):
                prompt += f"   [GOLDEN EXAMPLE]\n"
        
        prompt += """

Generate test cases in this JSON format:
[
  {
    "name": "Test case name",
    "input": "User input",
    "expected_behavior": "What the agent should do",
    "expected_output": "Expected response pattern",
    "difficulty": "basic|intermediate|advanced",
    "category": "session_management|git_operations|documentation|etc"
  }
]

Focus on:
1. Common patterns from the data
2. Edge cases
3. Multi-step workflows
4. Error handling scenarios
5. Real user needs

Return ONLY the JSON array, no other text.
"""
        
        return prompt
    
    def _parse_test_cases(self, text: str) -> List[Dict[str, Any]]:
        """Parse test cases from AI response."""
        # Extract JSON from response
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if not json_match:
            return []
        
        try:
            test_cases = json.loads(json_match.group())
            return test_cases
        except json.JSONDecodeError:
            return []
    
    def export_golden_examples(
        self,
        dataset_name: str,
        output_file: str
    ) -> int:
        """
        Export annotated golden examples.
        
        Args:
            dataset_name: Name of LangSmith dataset
            output_file: Output JSON file path
            
        Returns:
            Number of examples exported
        """
        # Get annotated examples
        examples = self.query_examples(
            dataset_name,
            filters={'annotated': True}
        )
        
        # Format for export
        export_data = []
        for ex in examples:
            inputs = getattr(ex, 'inputs', {}) or {}
            outputs = getattr(ex, 'outputs', {}) or {}
            metadata = getattr(ex, 'metadata', {}) or {}
            
            export_data.append({
                'input': inputs.get('prompt', ''),
                'output': outputs.get('response', ''),
                'metadata': metadata
            })
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return len(export_data)


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Query LLM logs and generate test cases'
    )
    parser.add_argument(
        '--dataset',
        required=True,
        help='LangSmith dataset name'
    )
    parser.add_argument(
        '--query',
        help='Search keyword'
    )
    parser.add_argument(
        '--generate-tests',
        action='store_true',
        help='Generate test cases'
    )
    parser.add_argument(
        '--num-tests',
        type=int,
        default=10,
        help='Number of test cases to generate'
    )
    parser.add_argument(
        '--export-golden',
        action='store_true',
        help='Export golden examples'
    )
    parser.add_argument(
        '--output',
        help='Output file path'
    )
    parser.add_argument(
        '--patterns',
        action='store_true',
        help='Detect patterns in dataset'
    )
    
    args = parser.parse_args()
    
    # Create querier
    querier = LLMLogQuerier()
    
    # Execute command
    if args.query:
        print(f"Searching for '{args.query}' in dataset '{args.dataset}'...")
        results = querier.search_by_keyword(args.dataset, args.query)
        print(f"Found {len(results)} matching examples")
        
        for i, ex in enumerate(results[:5], 1):
            inputs = getattr(ex, 'inputs', {}) or {}
            print(f"\n{i}. {inputs.get('prompt', '')[:100]}...")
    
    elif args.patterns:
        print(f"Detecting patterns in dataset '{args.dataset}'...")
        patterns = querier.detect_patterns(args.dataset)
        
        for pattern_type, items in patterns.items():
            print(f"\n{pattern_type.upper()}:")
            for item in items[:10]:
                print(f"  - {item}")
    
    elif args.generate_tests:
        print(f"Generating {args.num_tests} test cases from dataset '{args.dataset}'...")
        test_cases = querier.generate_test_cases(
            args.dataset,
            num_tests=args.num_tests
        )
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(test_cases, f, indent=2)
            print(f"Test cases saved to {args.output}")
        else:
            print(json.dumps(test_cases, indent=2))
    
    elif args.export_golden:
        if not args.output:
            print("Error: --output required for --export-golden")
            return
        
        print(f"Exporting golden examples from dataset '{args.dataset}'...")
        count = querier.export_golden_examples(args.dataset, args.output)
        print(f"Exported {count} golden examples to {args.output}")
    
    else:
        print("Error: Specify --query, --patterns, --generate-tests, or --export-golden")


if __name__ == '__main__':
    main()
