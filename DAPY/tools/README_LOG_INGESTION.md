# LLM Log Ingestion System

## Overview

Ingest your LLM conversation logs (MD/JSON) into LangSmith, annotate them, and automatically generate test cases.

**Workflow:**
```
Your LLM Logs (MD/JSON) 
  → Ingest to LangSmith
  → You Annotate (mark golden)
  → Manus Queries (generate tests)
  → Automated Test Cases
```

---

## Components

### 1. `ingest_llm_logs.py`
Ingests logs from various formats into LangSmith datasets.

**Supported Formats:**
- ChatGPT export (`conversations.json`)
- Claude export (JSON)
- Markdown files with conversations
- Custom JSON formats

### 2. `query_llm_logs.py`
Queries ingested logs and generates test cases using AI.

**Features:**
- Keyword search
- Pattern detection
- Automatic test case generation
- Golden example export

---

## Quick Start

### Step 1: Install Dependencies

```bash
cd /path/to/dapy
pip install -e .
pip install python-frontmatter
```

### Step 2: Set API Keys

```bash
export LANGCHAIN_API_KEY=ls-...
export OPENAI_API_KEY=sk-...
```

### Step 3: Ingest Your Logs

```bash
# Ingest from underscore repo
python tools/ingest_llm_logs.py \
  --source /path/to/_/Daily\ Notes \
  --dataset my-llm-logs \
  --recursive

# Ingest ChatGPT export
python tools/ingest_llm_logs.py \
  --source /path/to/chatgpt/conversations.json \
  --dataset my-llm-logs \
  --formats json

# Ingest Claude export
python tools/ingest_llm_logs.py \
  --source /path/to/claude/export.json \
  --dataset my-llm-logs \
  --formats json
```

### Step 4: Annotate in LangSmith UI

1. Go to https://smith.langchain.com
2. Navigate to Datasets → `my-llm-logs`
3. Review examples
4. Mark golden examples:
   - Edit metadata: `{"annotated": true, "quality": 5}`
   - Add notes: `{"notes": "Perfect example of X"}`

### Step 5: Query and Generate Tests

```bash
# Search for specific topics
python tools/query_llm_logs.py \
  --dataset my-llm-logs \
  --query "git operations"

# Detect patterns
python tools/query_llm_logs.py \
  --dataset my-llm-logs \
  --patterns

# Generate test cases
python tools/query_llm_logs.py \
  --dataset my-llm-logs \
  --generate-tests \
  --num-tests 20 \
  --output test_cases.json

# Export golden examples
python tools/query_llm_logs.py \
  --dataset my-llm-logs \
  --export-golden \
  --output golden_examples.json
```

---

## Supported Log Formats

### ChatGPT Export

**Format:** `conversations.json`

**Structure:**
```json
[
  {
    "id": "conv-123",
    "title": "Conversation Title",
    "create_time": 1234567890,
    "mapping": {
      "node-1": {
        "message": {
          "author": {"role": "user"},
          "content": {"parts": ["User message"]}
        }
      },
      "node-2": {
        "message": {
          "author": {"role": "assistant"},
          "content": {"parts": ["Assistant response"]}
        }
      }
    }
  }
]
```

**How to Export:**
1. Go to ChatGPT Settings
2. Data Controls → Export Data
3. Download `conversations.json`

### Claude Export

**Format:** JSON with conversations array

**Structure:**
```json
{
  "conversations": [
    {
      "uuid": "conv-456",
      "name": "Conversation Name",
      "created_at": "2025-01-26T12:00:00Z",
      "chat_messages": [
        {
          "sender": "human",
          "text": "User message"
        },
        {
          "sender": "assistant",
          "text": "Assistant response"
        }
      ]
    }
  ]
}
```

**How to Export:**
1. Go to Claude Settings
2. Privacy → Export Data
3. Download export file

### Markdown Files

**Format:** Markdown with conversation patterns

**Pattern 1: Headers**
```markdown
## User
What's next?

## Assistant
Current Status (from 2Do.md):
- Focus: Multi-Subagent Workflow
```

**Pattern 2: Blockquotes**
```markdown
> User: What's next?
> Assistant: Current Status...
```

**With Frontmatter:**
```markdown
---
date: 2025-01-26
category: Daily Note
tags: [llm, conversation]
---

## User
What's next?

## Assistant
Current Status...
```

### Custom JSON

**Format:** Generic conversation structure

**Structure:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "User message"
    },
    {
      "role": "assistant",
      "content": "Assistant response"
    }
  ]
}
```

---

## Annotation Workflow

### In LangSmith UI

**Step 1: Navigate to Dataset**
1. Open https://smith.langchain.com
2. Go to Datasets & Experiments
3. Select your dataset

**Step 2: Review Examples**
1. Click on an example
2. Review prompt and response
3. Assess quality

**Step 3: Annotate**
Edit metadata to mark as golden:
```json
{
  "annotated": true,
  "quality": 5,
  "notes": "Perfect example of session management",
  "tags": ["golden", "session", "whats-next"],
  "improvements": "None needed"
}
```

**Step 4: Use Annotation Queue (Optional)**
1. Create annotation queue
2. Add examples to queue
3. Batch review and annotate
4. Press `D` to add to dataset

### Programmatically

```python
from langsmith import Client

client = Client()
dataset = client.read_dataset(dataset_name="my-llm-logs")

# Get example
examples = list(client.list_examples(dataset_id=dataset.id))
example = examples[0]

# Update metadata
client.update_example(
    example_id=example.id,
    metadata={
        "annotated": True,
        "quality": 5,
        "notes": "Golden example",
        "tags": ["golden", "session"]
    }
)
```

---

## Query Interface

### Search by Keyword

```python
from tools.query_llm_logs import LLMLogQuerier

querier = LLMLogQuerier()

# Search in prompts
results = querier.search_by_keyword(
    dataset_name="my-llm-logs",
    keyword="git",
    search_in=["prompt"]
)

# Search in responses
results = querier.search_by_keyword(
    dataset_name="my-llm-logs",
    keyword="error",
    search_in=["response"]
)

# Search in both
results = querier.search_by_keyword(
    dataset_name="my-llm-logs",
    keyword="documentation",
    search_in=["both"]
)
```

### Filter by Metadata

```python
# Get only annotated examples
results = querier.query_examples(
    dataset_name="my-llm-logs",
    filters={"annotated": True}
)

# Get by source
results = querier.query_examples(
    dataset_name="my-llm-logs",
    filters={"source": "chatgpt"}
)

# Get by quality
results = querier.query_examples(
    dataset_name="my-llm-logs",
    filters={"quality": 5}
)

# Multiple filters
results = querier.query_examples(
    dataset_name="my-llm-logs",
    filters={
        "annotated": True,
        "quality": [4, 5],
        "source": ["chatgpt", "claude"]
    }
)
```

### Detect Patterns

```python
patterns = querier.detect_patterns(
    dataset_name="my-llm-logs",
    min_frequency=3
)

# Returns:
{
  "commands": ["what's next", "document", "close", "push"],
  "questions": ["What should I work on?", "How do I..."],
  "requests": ["Create a new...", "Update the..."],
  "topics": ["Git", "Documentation", "Testing"]
}
```

### Generate Test Cases

```python
test_cases = querier.generate_test_cases(
    dataset_name="my-llm-logs",
    num_tests=20,
    criteria={"annotated": True}
)

# Returns:
[
  {
    "name": "Session start with 'What's next?'",
    "input": "What's next?",
    "expected_behavior": "Read 2Do.md, check git status, provide summary",
    "expected_output": "Current status and recommended next steps",
    "difficulty": "basic",
    "category": "session_management"
  },
  ...
]
```

---

## Continuous Ingestion

### Watch Directory for New Logs

```bash
# Create watch script
cat > watch_logs.sh << 'EOF'
#!/bin/bash
while true; do
  python tools/ingest_llm_logs.py \
    --source /path/to/logs \
    --dataset my-llm-logs \
    --recursive
  sleep 3600  # Run every hour
done
EOF

chmod +x watch_logs.sh
./watch_logs.sh
```

### Scheduled Ingestion (Cron)

```bash
# Add to crontab
crontab -e

# Run every day at 2am
0 2 * * * cd /path/to/dapy && python tools/ingest_llm_logs.py --source /path/to/logs --dataset my-llm-logs
```

### Automated Annotation

```python
from langsmith import Client
from openai import OpenAI

client = Client()
openai_client = OpenAI()

# Get unannotated examples
dataset = client.read_dataset(dataset_name="my-llm-logs")
examples = list(client.list_examples(dataset_id=dataset.id))

for example in examples:
    metadata = getattr(example, 'metadata', {}) or {}
    
    if metadata.get('annotated'):
        continue
    
    # Use AI to assess quality
    inputs = getattr(example, 'inputs', {}) or {}
    outputs = getattr(example, 'outputs', {}) or {}
    
    prompt = f"""Assess this conversation:
User: {inputs.get('prompt', '')}
Assistant: {outputs.get('response', '')}

Rate quality (1-5) and suggest if it's a golden example.
Return JSON: {{"quality": N, "is_golden": true/false, "notes": "..."}}
"""
    
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    assessment = json.loads(response.choices[0].message.content)
    
    # Update metadata
    client.update_example(
        example_id=example.id,
        metadata={
            **metadata,
            "annotated": True,
            "quality": assessment["quality"],
            "is_golden": assessment["is_golden"],
            "notes": assessment["notes"],
            "auto_annotated": True
        }
    )
```

---

## Integration with DAPY

### Use Generated Tests

```python
# Generate tests from logs
test_cases = querier.generate_test_cases(
    dataset_name="my-llm-logs",
    num_tests=20
)

# Save to DAPY test suite
with open("dapy/tests/generated_tests.json", "w") as f:
    json.dump(test_cases, f, indent=2)

# Run tests
# (DAPY will load and execute these tests)
```

### Use Golden Examples for Prompt Optimization

```python
# Export golden examples
querier.export_golden_examples(
    dataset_name="my-llm-logs",
    output_file="dapy/prompts/golden_examples.json"
)

# Use in Prompt Canvas
# 1. Open LangSmith Prompt Canvas
# 2. Load golden examples
# 3. Test prompt variations
# 4. Optimize based on golden examples
```

---

## Best Practices

### For Ingestion

1. **Organize logs by source**
   ```
   /logs/
   ├── chatgpt/
   ├── claude/
   ├── cursor/
   └── daily-notes/
   ```

2. **Use descriptive dataset names**
   - `my-llm-logs-2025-01`
   - `chatgpt-work-conversations`
   - `claude-code-sessions`

3. **Ingest regularly**
   - Daily for active logs
   - Weekly for archives

4. **Check stats after ingestion**
   - Files processed
   - Conversations imported
   - Errors encountered

### For Annotation

1. **Start with high-quality examples**
   - Successful task completions
   - Clear user intent
   - Good assistant responses

2. **Use consistent criteria**
   - Quality: 1-5 scale
   - Tags: standardized set
   - Notes: specific and actionable

3. **Annotate in batches**
   - Use annotation queues
   - Set aside dedicated time
   - Review 10-20 examples per session

4. **Involve domain experts**
   - You know your workflow best
   - Mark examples that represent ideal behavior
   - Note edge cases and exceptions

### For Querying

1. **Start broad, then narrow**
   - Detect patterns first
   - Search by topic
   - Filter by quality

2. **Validate generated tests**
   - Review AI-generated test cases
   - Adjust as needed
   - Add missing scenarios

3. **Iterate on test generation**
   - Start with 10 tests
   - Review and refine
   - Generate more as needed

---

## Troubleshooting

### Ingestion Issues

**Problem:** No examples created
- Check file format
- Verify conversation structure
- Look for parsing errors in output

**Problem:** Metadata missing
- Ensure frontmatter in MD files
- Check JSON structure
- Verify field names

**Problem:** Duplicate examples
- Dataset doesn't auto-deduplicate
- Filter by source_file to check
- Manually remove if needed

### Query Issues

**Problem:** No results from search
- Check keyword spelling
- Try broader search terms
- Verify dataset name

**Problem:** Test generation fails
- Check OpenAI API key
- Verify dataset has examples
- Try with smaller num_tests

**Problem:** Pattern detection empty
- Increase min_frequency
- Check if dataset has enough examples
- Verify conversation format

---

## API Reference

### LLMLogIngester

```python
class LLMLogIngester:
    def __init__(self, api_key: Optional[str] = None)
    
    def ingest_directory(
        self,
        source_dir: str,
        dataset_name: str,
        recursive: bool = True,
        formats: List[str] = None
    ) -> Dict[str, int]
```

### LLMLogQuerier

```python
class LLMLogQuerier:
    def __init__(
        self,
        langsmith_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None
    )
    
    def query_examples(
        self,
        dataset_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]
    
    def search_by_keyword(
        self,
        dataset_name: str,
        keyword: str,
        search_in: List[str] = None
    ) -> List[Dict[str, Any]]
    
    def detect_patterns(
        self,
        dataset_name: str,
        min_frequency: int = 3
    ) -> Dict[str, List[str]]
    
    def generate_test_cases(
        self,
        dataset_name: str,
        num_tests: int = 10,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]
    
    def export_golden_examples(
        self,
        dataset_name: str,
        output_file: str
    ) -> int
```

---

## Examples

### Complete Workflow

```bash
# 1. Ingest all your logs
python tools/ingest_llm_logs.py \
  --source ~/_ \
  --dataset my-complete-logs \
  --recursive

# 2. Detect patterns
python tools/query_llm_logs.py \
  --dataset my-complete-logs \
  --patterns

# 3. Search for specific topics
python tools/query_llm_logs.py \
  --dataset my-complete-logs \
  --query "git operations"

# 4. Annotate in LangSmith UI
# (mark golden examples)

# 5. Generate test cases
python tools/query_llm_logs.py \
  --dataset my-complete-logs \
  --generate-tests \
  --num-tests 50 \
  --output dapy_tests.json

# 6. Export golden examples
python tools/query_llm_logs.py \
  --dataset my-complete-logs \
  --export-golden \
  --output golden_examples.json
```

### Programmatic Usage

```python
from tools.ingest_llm_logs import LLMLogIngester
from tools.query_llm_logs import LLMLogQuerier

# Ingest
ingester = LLMLogIngester()
stats = ingester.ingest_directory(
    source_dir="/path/to/logs",
    dataset_name="my-logs"
)
print(f"Imported {stats['examples_created']} examples")

# Query
querier = LLMLogQuerier()

# Find git-related conversations
git_examples = querier.search_by_keyword("my-logs", "git")

# Generate tests
tests = querier.generate_test_cases("my-logs", num_tests=20)

# Export golden
count = querier.export_golden_examples("my-logs", "golden.json")
print(f"Exported {count} golden examples")
```

---

## Summary

**What This System Does:**
1. ✅ Ingests your LLM logs (MD/JSON) into LangSmith
2. ✅ Enables annotation workflow (mark golden examples)
3. ✅ Allows querying and pattern detection
4. ✅ Automatically generates test cases using AI
5. ✅ Exports golden examples for prompt optimization

**Benefits:**
- ✅ All your LLM history in one place
- ✅ Easy annotation and curation
- ✅ Automatic test generation
- ✅ Data-driven development
- ✅ Continuous improvement

**Next Steps:**
1. Ingest your logs
2. Annotate golden examples
3. Generate test cases
4. Use for DAPY testing
5. Iterate and improve
