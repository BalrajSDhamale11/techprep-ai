"""
TechPrep AI — MCP Connection Verification Test
Run this to confirm the agent can communicate with the MCP server
via the protocol before launching the playground.

Usage: python tests/test_mcp_connection.py
"""

import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the agent's MCP client function
from app.agent import call_mcp_server

print("TechPrep AI — MCP Connection Test")
print("=" * 50)
print(f"MCP Server: {PROJECT_ROOT / 'mcp_server' / 'question_bank_server.py'}")
print()

tests = [
    {
        "name": "list_topics tool",
        "tool": "list_topics",
        "args": {},
        "check_key": "available_topics",
        "check_description": "Returns list of topic names"
    },
    {
        "name": "get_question tool (arrays easy)",
        "tool": "get_question",
        "args": {"topic": "arrays", "difficulty": "easy"},
        "check_key": "question",
        "check_description": "Returns a real interview question"
    },
    {
        "name": "get_question tool (behavioral general)",
        "tool": "get_question",
        "args": {"topic": "behavioral", "difficulty": "general"},
        "check_key": "question",
        "check_description": "Returns a behavioral question"
    },
    {
        "name": "get_random_question tool",
        "tool": "get_random_question",
        "args": {"exclude_topic": "behavioral"},
        "check_key": "topic",
        "check_description": "Returns a random technical question"
    }
]

passed = 0
failed = 0

for test in tests:
    print(f"Testing: {test['name']}")
    print(f"  Description: {test['check_description']}")

    result = call_mcp_server(test["tool"], test["args"])

    if "error" in result:
        print(f"  FAILED — Error: {result['error']}")
        failed += 1
    elif test["check_key"] not in result:
        print(f"  FAILED — Expected key '{test['check_key']}' not in response")
        print(f"  Got keys: {list(result.keys())}")
        failed += 1
    else:
        value_preview = str(result[test["check_key"]])[:80]
        print(f"  PASSED — {test['check_key']}: {value_preview}...")
        passed += 1

    print()

print("=" * 50)
print(f"Results: {passed}/{len(tests)} tests passed")

if passed == len(tests):
    print()
    print("MCP integration is working correctly.")
    print("The agent will communicate with the server via MCP protocol.")
else:
    print()
    print(f"{failed} test(s) failed.")
    print("Check that mcp_server/question_bank_server.py exists and runs:")
    print(f"  python {PROJECT_ROOT / 'mcp_server' / 'question_bank_server.py'}")
    sys.exit(1)