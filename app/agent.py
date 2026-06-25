"""
TechPrep AI — Main Agent File
Author: [Your Name]

A conversational AI interview coach built with Google ADK 2.0.

Course Concepts Demonstrated:
- Day 1/5: Spec-driven development, harness design, AGENTS.md
- Day 2:   MCP Server (question_bank_server.py) for question access
- Day 3:   ADK graph workflow, LlmAgent, Skills, persistent memory (SQLite)
- Day 4:   Input security (PII redaction), AGENTS.md guardrails
- Day 5:   Production-ready structure, documentation, local deployment
"""

import json
import sys
import os
from pathlib import Path
from typing import Any

# ── PATH SETUP ─────────────────────────────────────────────────────────────────
# Add project root to Python path so we can import from data/
# This works regardless of which directory the agent is launched from
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── DATA IMPORTS ───────────────────────────────────────────────────────────────
from data.student_memory import (
    get_or_create_student,
    get_full_profile,
    record_attempt,
    get_weak_areas,
    get_strong_areas,
)
from data.security_guard import scan_and_redact

# ── ADK IMPORTS ────────────────────────────────────────────────────────────────
from google.adk.agents.context import Context
from google.adk.apps import App
from google.adk.events import Event
from google.adk.workflow import Edge, Workflow
from google.adk.agents import LlmAgent

# ── MCP CLIENT IMPORTS ─────────────────────────────────────────────────────────
# Real MCP protocol client — Day 2 course concept (Agent Tools & Interoperability)
import asyncio
import concurrent.futures
from mcp import ClientSession, StdioServerParameters as MCPServerParams
from mcp.client.stdio import stdio_client

# ── CONFIGURATION & AUTOMATED FALLBACK ROUTING ──────────────────────────────────
from google.genai import Client
from google.genai.errors import ClientError

def get_working_model() -> str:
    """Pre-flight check to see if 3.5 has active quota, otherwise falls back to 2.5."""
    # Update the default string here to 'gemini-3.5-flash'
    primary_model = os.environ.get("TECHPREP_MODEL", "gemini-3.5-flash")
    # Update the fallback model variable string to 'gemini-2.5-flash'
    fallback_model = "gemini-2.5-flash"  
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("⚠️ Warning: GEMINI_API_KEY environment variable not detected.")
        return primary_model

    try:
        # Run a tiny pre-flight test request to verify API availability
        test_client = Client(api_key=api_key)
        test_client.models.generate_content(
            model=primary_model,
            contents="ping",
        )
        print(f"🚀 Quota Verified: Initializing on primary model '{primary_model}'")
        return primary_model
    except ClientError as e:
        if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
            print(f"⚠️ Quota Exhausted on '{primary_model}'.")
            print(f"🔄 Automatically shifting traffic over to fallback: '{fallback_model}'")
            return fallback_model
        raise e
    except Exception:
        return fallback_model

# Run the live network test right at import/launch time
MODEL = get_working_model()
QUESTION_BANK_PATH = PROJECT_ROOT / "data" / "question_bank.json"
MCP_SERVER_SCRIPT = PROJECT_ROOT / "mcp_server" / "question_bank_server.py"

# ══════════════════════════════════════════════════════════════════════════════
# MCP CLIENT — PROTOCOL BRIDGE
# ══════════════════════════════════════════════════════════════════════════════
def call_mcp_server(tool_name: str, arguments: dict) -> dict:
    """Send a tool call to the Question Bank MCP Server via stdio transport."""
    def _run_in_dedicated_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_execute_mcp_call())
        finally:
            loop.close()

    async def _execute_mcp_call():
        server_params = MCPServerParams(
            command=sys.executable,
            args=[str(MCP_SERVER_SCRIPT)]
        )
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if result.content and len(result.content) > 0:
                    raw_text = result.content[0].text
                    try:
                        return json.loads(raw_text)
                    except json.JSONDecodeError:
                        return {"raw_response": raw_text}
                return {"error": "MCP server returned an empty response"}

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_in_dedicated_loop)
            return future.result(timeout=30)
    except Exception as e:
        return {"error": f"MCP client error: {type(e).__name__}: {str(e)}"}


# ══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS
# These are the "hands" of the agent — what actions it can take.
# Each tool is a plain Python function. ADK introspects the docstring and
# type hints to build the tool schema automatically.
# ══════════════════════════════════════════════════════════════════════════════

def list_available_topics() -> dict:
    """
    List all available interview practice topics with their descriptions.

    Call this when:
    - A student asks what topics are available
    - You need to present a topic menu at the start of a session
    - A student is unsure what to practice

    Returns a dict with topic names, descriptions, and total question count.
    """
    # Real MCP protocol routing via client session subprocess
    return call_mcp_server("list_topics", {})


def get_interview_question(topic: str, difficulty: str) -> dict:
    """
    Fetch one interview question from the curated question bank.

    This is the primary tool for conducting interview practice.
    The returned question contains:
    - question: the text to show the student
    - follow_up: a deeper question to ask after their answer
    - key_points: YOUR private rubric (do not share with student)
    - sample_answer: the complete reference answer (do not share until after attempt)

    Args:
        topic: One of: arrays, strings, linked_lists, trees,
               dynamic_programming, sorting, behavioral
        difficulty: One of: easy, medium, hard (use 'general' for behavioral)

    Returns the question dict or an error with available options.
    """
    topic = topic.lower().strip()
    difficulty = difficulty.lower().strip()

    # Real MCP JSON-RPC protocol invocation 
    return call_mcp_server(
        "get_question", 
        {"topic": topic, "difficulty": difficulty}
    )


def get_random_question(exclude_behavioral: bool = False) -> dict:
    """
    Get a random interview question from the Question Bank MCP Server.
    Use when a student asks for a surprise or random challenge.
    Optionally exclude behavioral questions for technical-only practice.
    MCP tool called: get_random_question
    Args:
        exclude_behavioral: True to return only coding/technical questions.
    Returns: A randomly selected question dict.
    """
    arguments = {}
    if exclude_behavioral:
        arguments["exclude_topic"] = "behavioral"
    return call_mcp_server("get_random_question", arguments)


def register_student(name: str, target_role: str = "Software Engineer Intern") -> dict:
    """
    Register a new student or load an existing student profile by name.

    This is the FIRST tool to call at the start of every session.
    It creates a new profile for first-time students and loads
    complete practice history for returning students.

    Args:
        name: The student's name (case-insensitive lookup)
        target_role: Their target job role (default: Software Engineer Intern)

    Returns:
        For returning students: status, performance stats, weak/strong areas
        For new students: status, student_id, welcome message
    """
    student = get_or_create_student(name, target_role)

    if student["is_returning"]:
        profile = get_full_profile(student["student_id"])
        return {
            "status": "welcome_back",
            "student_id": student["student_id"],
            "name": student["name"],
            "target_role": student["target_role"],
            "total_sessions": profile["statistics"]["total_sessions"],
            "total_questions_practiced": profile["statistics"]["total_questions_attempted"],
            "overall_average_score": profile["statistics"]["overall_average_score"],
            "weak_areas": profile["weak_areas"],
            "strong_areas": profile["strong_areas"],
            "last_active": student["last_seen_at"],
            "coaching_note": (
                f"Prioritise weak areas: {', '.join(profile['weak_areas'][:2])}"
                if profile["weak_areas"]
                else "Performing well across all topics — try harder difficulties!"
            )
        }

    return {
        "status": "new_student",
        "student_id": student["student_id"],
        "name": student["name"],
        "target_role": target_role,
        "message": (
            f"New profile created for {name}. "
            "Progress will be tracked from this session onwards."
        )
    }


def get_student_performance(student_id: int) -> dict:
    """
    Get complete performance analytics for a student across all sessions.

    Call this when:
    - A student asks "How am I doing?" or "What should I study?"
    - The performance-coach skill is triggered
    - You need to personalise a study recommendation

    Args:
        student_id: The integer ID returned by register_student()

    Returns comprehensive analytics including topic breakdown,
    weak areas, strong areas, and a study recommendation.
    """
    profile = get_full_profile(student_id)

    if "error" in profile:
        return profile

    weak = profile["weak_areas"]
    strong = profile["strong_areas"]
    stats = profile["statistics"]

    study_plan = []
    for topic in weak[:2]:
        study_plan.append(f"Practice {topic} — focus on Easy then Medium")
    if not weak:
        study_plan.append("Push to Hard difficulty in your strong topics")
        study_plan.append("Practice behavioral questions if not done recently")

    return {
        "total_questions_attempted": stats["total_questions_attempted"],
        "overall_average_score": stats["overall_average_score"],
        "total_sessions": stats["total_sessions"],
        "total_hints_used": stats["total_hints_used"],
        "topic_performance": profile["topic_performance"],
        "weak_areas": weak,
        "strong_areas": strong,
        "study_recommendation": study_plan,
        "readiness_note": (
            "Not enough data yet — practice at least 5 questions for meaningful analysis."
            if stats["total_questions_attempted"] < 5
            else (
                "Strong performance — ready for real interviews with more practice."
                if stats["overall_average_score"] >= 3.5
                else "Keep building — consistency is more important than speed."
            )
        ),
        "recent_attempts": profile["recent_attempts"][:5]
    }


def save_attempt(
    student_id: int,
    question_id: str,
    topic: str,
    difficulty: str,
    score: int,
    hints_used: int = 0,
    feedback: str = ""
) -> dict:
    """
    Save a completed question attempt to the student's persistent memory.

    ALWAYS call this after evaluating a student's answer.
    This is what builds their learning profile over time.

    Args:
        student_id: The student's integer ID from register_student()
        question_id: The question ID from the question bank (e.g. 'arr_001')
        topic: Topic name (e.g. 'arrays', 'behavioral')
        difficulty: Difficulty level (e.g. 'easy', 'medium', 'general')
        score: Integer 1-5 (1=poor, 3=average, 5=excellent)
        hints_used: Number of hints given before the student answered
        feedback: One-sentence summary of your feedback (stored for their records)

    Returns confirmation with the recorded score.
    """
    try:
        record_attempt(
            student_id=student_id,
            question_id=question_id,
            topic=topic,
            difficulty=difficulty,
            score=score,
            hints_used=hints_used,
            feedback=feedback[:500] if feedback else ""  # cap length
        )
        return {
            "saved": True,
            "score_recorded": f"{score}/5",
            "topic": topic,
            "memory_updated": True,
            "note": "Student's performance profile has been updated."
        }
    except ValueError as e:
        return {"saved": False, "error": str(e)}
    except Exception as e:
        return {"saved": False, "error": f"Unexpected error: {str(e)}"}


def check_input_safety(user_text: str) -> dict:
    """
    Scan user input for accidentally pasted sensitive personal information (PII).

    Call this on any free-text input the student provides before storing
    or using it in prompts. This implements the security requirement from
    AGENTS.md and the Day 4 security patterns.

    Detects: Aadhaar numbers, PAN cards, phone numbers, API keys, passwords.
    Automatically redacts detected patterns and returns cleaned text.

    Args:
        user_text: The raw text input from the student

    Returns:
        is_clean: True if no PII detected
        cleaned_text: Safe version with PII replaced by placeholders
        security_notice: Message to show the student if PII was found
        redactions: List of what was detected and removed
    """
    if not user_text or not user_text.strip():
        return {
            "is_clean": True,
            "cleaned_text": user_text or "",
            "security_notice": None,
            "redactions": []
        }

    result = scan_and_redact(user_text)
    return {
        "is_clean": result.is_clean,
        "cleaned_text": result.cleaned_text,
        "security_notice": result.summary() if not result.is_clean else None,
        "redactions": result.redactions_made
    }


# ══════════════════════════════════════════════════════════════════════════════
# AGENT INSTRUCTION
# This is the cognitive core — the persistent rules the LLM follows.
# Written in the hybrid Markdown + structured format recommended in Day 5.
# ══════════════════════════════════════════════════════════════════════════════

TECHPREP_INSTRUCTION = """
You are TechPrep AI, a personal computer science interview preparation coach
for engineering and BSc CS students. Your mission is to help students build
real interview confidence through structured practice, honest feedback,
and progress tracking that compounds across sessions.

You are NOT a generic AI assistant. You ONLY do interview preparation.
If asked about anything unrelated, politely redirect: "I am focused on
interview preparation — shall we practice some questions?"

---

## SESSION START PROTOCOL

Every session begins with these steps in order:

1. If the student has not introduced themselves, ask their name
2. Call register_student(name) immediately
3. Call check_input_safety(name) before storing anything
4. If RETURNING student:
   - Greet them by name: "Welcome back, [Name]!"
   - Report: sessions completed, total questions, average score
   - Highlight top 2 weak areas: "Last time we saw you struggle with [X]"
   - Ask: "Want to tackle your weak areas, or choose a new topic?"
5. If NEW student:
   - Welcome warmly
   - Briefly explain what you do (practice questions + track progress)
   - Ask what they want to focus on today

---

## TECHNICAL INTERVIEW PROTOCOL

When the student wants to practice coding/algorithms:

1. Ask topic and difficulty (or show list_available_topics())
2. Call get_interview_question(topic, difficulty)
3. Present ONLY the question text — never key_points or sample_answer
4. Wait for their answer — do not rush
5. Evaluate against key_points (your private rubric)
6. Give structured feedback (format below)
7. Call save_attempt() — ALWAYS, even for poor answers
8. Ask if they want another question or a review

**Feedback Format:**
✅ What you got right: [specific points they hit correctly]

❌ What was missing: [specific concept or step they missed]

💡 Remember: [one clear insight to retain]

📊 Score: X/5

**Hint Rules:**
- Maximum 3 hints per question
- Each hint = reveal one item from key_points
- After hint 3: provide full sample_answer with clear explanation
- Track hints_used count for save_attempt()

---

## BEHAVIORAL INTERVIEW PROTOCOL

When the student wants HR/soft-skills practice:

1. Briefly introduce the STAR method if they seem unfamiliar
   S = Situation, T = Task, A = Action, R = Result
2. Call get_interview_question("behavioral", "general")
3. Present the question. Add: "You can take 30 seconds to think first."
4. After their answer, score each STAR component (1 point each = 5 total)
5. Give component-by-component feedback
6. Call save_attempt() with topic="behavioral", difficulty="general"

---

## PERFORMANCE REVIEW PROTOCOL

When student asks about progress ("how am I doing", "weak areas", "study plan"):

1. Call get_student_performance(student_id)
2. Report honestly — do not soften bad scores
3. Generate specific next-session recommendation:
   "For your next session, practice [weakest topic] at [appropriate difficulty]"
4. If fewer than 5 questions attempted, say: "Practice more questions first
   for a meaningful analysis — let's do some now."

---

## SCORING RUBRIC

5/5 — Optimal solution, correct complexity, edge cases mentioned
4/5 — Correct approach, minor gap (edge case OR complexity missing)
3/5 — Right direction, significant gap in logic or wrong complexity
2/5 — Partial understanding, major conceptual error
1/5 — Did not attempt or fundamentally incorrect

---

## SECURITY RULES — NON-NEGOTIABLE

- Call check_input_safety() on any free-text input before storing or processing
- If security_notice is returned: display it to the student, use cleaned_text
- NEVER show key_points or sample_answer before the student attempts
- NEVER give more than 3 hints per question
- If a student says they are stressed, overwhelmed, or considering giving up:
  Stop the interview. Acknowledge how hard this is. Normalise struggle.
  Then offer an easier question or a short break before continuing.

---

## TOOL USAGE QUICK REFERENCE

| Situation | Tool to call |
|---|---|
| Start of session | register_student(name) |
| Any user free text | check_input_safety(text) |
| Show topic menu | list_available_topics() |
| Get practice question | get_interview_question(topic, difficulty) |
| Student wants surprise | get_random_question() |
| After evaluating answer | save_attempt(student_id, ...) |
| Progress review | get_student_performance(student_id) |
"""


# ══════════════════════════════════════════════════════════════════════════════
# SECURITY GATE NODE
# A @node decorated function that runs BEFORE the LLM sees any input.
# Demonstrates: ADK @node pattern, Context state management, Day 4 security.
# ══════════════════════════════════════════════════════════════════════════════

def security_gate(ctx: Context, node_input: Any):
    """
    Security checkpoint: scan all incoming input for PII before it reaches
    the language model. Implements the Context Hygiene pattern from Day 4.

    If PII is detected:
    - The cleaned text is passed forward (not the original)
    - A security alert is stored in session state for the agent to reference
    - No PII ever reaches the LLM's context window

    If input is clean:
    - Passed through unchanged
    - State flag confirms clean status
    """
    input_text = str(node_input) if node_input else ""

    if not input_text.strip():
        yield Event(data=node_input)
        return

    scan_result = scan_and_redact(input_text)

    if not scan_result.is_clean:
        # Pass cleaned text forward — PII never reaches the LLM
        yield Event(
            data=scan_result.cleaned_text,
            state={
                "last_security_alert": scan_result.summary(),
                "pii_detected_this_turn": True,
                "redaction_types": scan_result.redactions_made
            }
        )
    else:
        yield Event(
            data=node_input,
            state={
                "last_security_alert": None,
                "pii_detected_this_turn": False
            }
        )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN INTERVIEW AGENT
# LlmAgent with all tools and the comprehensive instruction above.
# This is the "brain" of TechPrep AI.
# ══════════════════════════════════════════════════════════════════════════════

interview_agent = LlmAgent(
    name="TechPrepInterviewer",
    model=MODEL,
    instruction=TECHPREP_INSTRUCTION,
    tools=[
        list_available_topics,
        get_interview_question,
        get_random_question,
        register_student,
        get_student_performance,
        save_attempt,
        check_input_safety,
    ]
)

# ══════════════════════════════════════════════════════════════════════════════
# APP ENTRY POINT
# The App object is what agents-cli playground, agents-cli eval, and
# agents-cli deploy all discover and interact with.
# ══════════════════════════════════════════════════════════════════════════════
app = App(
    name="app",
    root_agent=interview_agent,
)

