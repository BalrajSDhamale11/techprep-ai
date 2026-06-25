#!/usr/bin/env python3
"""
TechPrep AI — Question Bank MCP Server

This MCP server exposes curated CS interview questions to the TechPrep AI agent.
It runs as a separate process and communicates via the stdio transport.

Course concept demonstrated: MCP (Day 2 — Agent Tools & Interoperability)
"""

import json
import random
import asyncio
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Locate question bank relative to this file — works regardless of working directory
DATA_FILE = Path(__file__).parent.parent / "data" / "question_bank.json"

def load_question_bank() -> dict:
    """Load the question bank from JSON file."""
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Question bank not found at {DATA_FILE}. "
            "Ensure data/question_bank.json exists in the project root."
        )
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Initialize the MCP server
server = Server("techprep-question-bank")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Advertise available tools to the connecting agent."""
    return [
        Tool(
            name="list_topics",
            description=(
                "List all available interview topics and their descriptions. "
                "Use this when a student asks what topics are available to practice."
            ),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_question",
            description=(
                "Get one interview question for a specific topic and difficulty. "
                "Use this when the student has chosen a topic and difficulty to practice. "
                "Returns the question, follow-up prompt, key points, and sample answer."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": (
                            "The interview topic. Must be one of: arrays, strings, "
                            "linked_lists, trees, dynamic_programming, sorting, behavioral"
                        )
                    },
                    "difficulty": {
                        "type": "string",
                        "description": (
                            "The difficulty level. Must be one of: easy, medium, hard, general "
                            "(use 'general' for behavioral questions)"
                        )
                    }
                },
                "required": ["topic", "difficulty"]
            }
        ),
        Tool(
            name="get_questions_for_topic",
            description=(
                "Get a list of all available questions for a specific topic. "
                "Use this to show the student what is available before they choose, "
                "or to find weak areas that have multiple questions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The interview topic to list questions for."
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="get_random_question",
            description=(
                "Get a random interview question. Optionally filter by difficulty. "
                "Use this when a student says they want a surprise or random question."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "difficulty": {
                        "type": "string",
                        "description": (
                            "Optional difficulty filter: easy, medium, hard. "
                            "Leave empty for any difficulty."
                        )
                    },
                    "exclude_topic": {
                        "type": "string",
                        "description": (
                            "Optional topic to exclude (e.g., 'behavioral' for technical-only). "
                            "Leave empty to include all topics."
                        )
                    }
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls from the agent."""
    try:
        data = load_question_bank()
        questions = data["questions"]

        if name == "list_topics":
            result = {
                "available_topics": list(data["topics"].keys()),
                "topic_descriptions": data["topics"],
                "total_questions": len(questions),
                "usage_tip": (
                    "Call get_question with a topic and difficulty to get a specific question. "
                    "Call get_random_question for a surprise."
                )
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_question":
            topic = arguments.get("topic", "").lower().strip()
            difficulty = arguments.get("difficulty", "").lower().strip()

            matching = [
                q for q in questions
                if q["topic"] == topic and q["difficulty"] == difficulty
            ]

            if not matching:
                available = list(data["topics"].keys())
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": (
                            f"No questions found for topic='{topic}' "
                            f"difficulty='{difficulty}'."
                        ),
                        "available_topics": available,
                        "hint": (
                            "Use list_topics to see all options. "
                            "Behavioral questions use difficulty='general'."
                        )
                    }, indent=2)
                )]

            # Pick a random question from matching ones for variety
            question = random.choice(matching)
            return [TextContent(type="text", text=json.dumps(question, indent=2))]

        elif name == "get_questions_for_topic":
            topic = arguments.get("topic", "").lower().strip()
            matching = [q for q in questions if q["topic"] == topic]

            if not matching:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": f"No questions found for topic '{topic}'.",
                        "available_topics": list(data["topics"].keys())
                    }, indent=2)
                )]

            summary = {
                "topic": topic,
                "total_count": len(matching),
                "by_difficulty": {},
                "questions": []
            }

            for q in matching:
                diff = q["difficulty"]
                summary["by_difficulty"][diff] = summary["by_difficulty"].get(diff, 0) + 1
                summary["questions"].append({
                    "id": q["id"],
                    "difficulty": q["difficulty"],
                    "type": q["type"],
                    "preview": q["question"][:120] + "..." if len(q["question"]) > 120 else q["question"]
                })

            return [TextContent(type="text", text=json.dumps(summary, indent=2))]

        elif name == "get_random_question":
            difficulty = arguments.get("difficulty", "").lower().strip()
            exclude_topic = arguments.get("exclude_topic", "").lower().strip()

            filtered = questions
            if difficulty:
                filtered = [q for q in filtered if q["difficulty"] == difficulty]
            if exclude_topic:
                filtered = [q for q in filtered if q["topic"] != exclude_topic]

            if not filtered:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "No questions match the specified filters."}, indent=2)
                )]

            question = random.choice(filtered)
            return [TextContent(type="text", text=json.dumps(question, indent=2))]

        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2)
            )]

    except FileNotFoundError as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, indent=2)
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Server error: {str(e)}"}, indent=2)
        )]

async def main():
    """Start the MCP server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)

if __name__ == "__main__":
    asyncio.run(main())