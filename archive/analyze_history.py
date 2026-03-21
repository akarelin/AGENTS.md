import os
import json
import glob
from collections import Counter
import re

def analyze_history():
    history_files = glob.glob('D:/SD/.claude/**/history.jsonl', recursive=True)
    all_displays = []
    
    for file_path in history_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if 'display' in data:
                            all_displays.append(data['display'].strip())
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    # Top commands
    counter = Counter(all_displays)
    print("--- Top 20 Commands ---")
    for cmd, count in counter.most_common(20):
        print(f"{count:4} | {cmd}")

    # Pattern analysis
    # Common verbs
    verbs = ['fix', 'add', 'create', 'search', 'find', 'archive', 'document', 'push', 'close', 'what\'s next', 'analyze', 'implement']
    verb_counts = Counter()
    for cmd in all_displays:
        cmd_lower = cmd.lower()
        for v in verbs:
            if v in cmd_lower:
                verb_counts[v] += 1
    
    print("\n--- Command Patterns (Verbs) ---")
    for verb, count in verb_counts.most_common():
        print(f"{count:4} | {verb}")

    # Tool-like commands (starting with /)
    slash_commands = [cmd for cmd in all_displays if cmd.startswith('/')]
    slash_counter = Counter(slash_commands)
    print("\n--- Top Slash Commands ---")
    for cmd, count in slash_counter.most_common(10):
        print(f"{count:4} | {cmd}")

if __name__ == "__main__":
    analyze_history()
