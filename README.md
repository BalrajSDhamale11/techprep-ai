# TechPrep AI 🎯
### Your Personal CS Interview Preparation Coach — Powered by AI Agents

> Built for Kaggle's 5-Day AI Agents: Intensive Vibe Coding Course with Google  
> Track: **Concierge Agents** > Author: Balraj S Dhamale  
> Repository: https://github.com/BalrajSDhamale11/techprep-ai

---

## The Problem

Every CS and engineering student preparing for internship and placement
interviews faces the same three gaps:

**Gap 1 — No structured feedback loop.**
Practicing on LeetCode gives you a verdict (pass/fail) but not a coaching
conversation. Students don't know *why* their answer was wrong or *what*
mental model they are missing.

**Gap 2 — No memory across sessions.**
Every practice session starts from zero. There is no system that remembers
you struggled with dynamic programming last Tuesday and recommends you
revisit it today with a different question.

**Gap 3 — No personalised study plan.**
Generic interview prep advice ("practice arrays and strings") ignores each
student's specific weak areas, available time, and target company.

These three gaps are exactly what AI agents — not chatbots, not scripts —
are uniquely equipped to solve.

---

## The Solution

TechPrep AI is a conversational AI interview coach that:

- Conducts realistic mock interviews for technical and behavioral questions
- Evaluates answers with structured, specific feedback scored 1–5
- Remembers every student's practice history across sessions (persistent SQLite memory)
- Identifies weak areas automatically from score patterns
- Generates a personalised next-session study plan based on real performance data
- Protects student privacy by redacting sensitive personal information before it reaches the LLM

Unlike a chatbot, TechPrep AI has **agency**: it decides which question to
fetch, calls external tools via protocol, tracks state across multiple turns,
updates a persistent student profile after every answer, and adapts its
coaching based on accumulated performance data.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                        STUDENT (Terminal / Web UI)              │
└────────────────────────────┬────────────────────────────────────┘
                             │ Natural language input
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ADK 2.0 GRAPH WORKFLOW                        │
│                                                                 │
│   START → [security_gate node] → [TechPrepInterviewer LlmAgent] │
│                                                                 │
│   security_gate:                                                │
│   • Scans input for PII (Aadhaar, PAN, phone, API keys)         │
│   • Redacts sensitive patterns before LLM sees them             │
│   • Stores security alert in session state if triggered         │
│   • Passes cleaned text forward to the LLM agent                │
│                                                                 │
│   TechPrepInterviewer (gemini-3.5-flash):                       │
│   • Reads AGENTS.md rules (hard constraints, guardrails)        │
│   • Activates skills based on student intent                    │
│   • Calls tools to fetch questions, save progress, check PII    │
└────────────┬────────────────────┬───────────────────────────────┘
             │                    │
             ▼                    ▼
┌────────────────────┐  ┌─────────────────────────────────────────┐
│  MCP SERVER        │  │  LOCAL PYTHON TOOLS                     │
│  (subprocess)      │  │                                         │
│                    │  │  register_student()                     │
│  question_bank_    │  │  • get_or_create student in SQLite      │
│  server.py         │  │  • returns full history if returning    │
│                    │  │                                         │
│  JSON-RPC 2.0      │  │  save_attempt()                         │
│  over stdio        │  │  • writes score, topic, feedback to DB  │
│                    │  │                                         │
│  Tools exposed:    │  │  get_student_performance()              │
│  • list_topics     │  │  • analytics: weak/strong areas         │
│  • get_question    │  │  • generates study plan                 │
│  • get_random_q    │  │                                         │
│  • get_questions   │  │  check_input_safety()                   │
│    _for_topic      │  │  • PII scan on any free-text input      │
└────────────────────┘  └─────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────────┐
│  DATA LAYER                                                    │
│                                                                │
│  data/question_bank.json     — 18 curated questions,           │
│                                 7 topics, 3 difficulty levels  │
│                                                                │
│  data/techprep_memory.db     — SQLite: students, attempts,     │
│                                 sessions tables                │
└────────────────────────────────────────────────────────────────┘
```

### Skills Architecture (Day 3 — Progressive Disclosure)

```text
.agents/skills/
│
├── technical-interviewer/        ← Level 2: Instructions + Resources
│   ├── SKILL.md                   Triggers on: coding, DSA, algorithm questions
│   └── resources/
│       └── complexity_guide.md    Big-O reference — loaded only when skill fires
│
├── behavioral-interviewer/       ← Level 3: Instructions + Examples (Few-Shot)
│   ├── SKILL.md                   Triggers on: HR, soft skills, STAR questions
│   └── examples/
│       └── star_example.txt       Strong vs weak STAR answer — calibrates scoring
│
└── performance-coach/            ← Level 1: Instructions Only
    └── SKILL.md                   Triggers on: progress, weak areas, study plan
```

Each skill loads **only** when the student's intent matches its description
field — this is the **progressive disclosure** pattern from the Day 3
whitepaper, which achieves up to 98% reduction in active context tokens
compared to loading all capabilities at startup.

---

## Course Concepts Demonstrated

This project intentionally demonstrates all six course concepts from the
5-Day AI Agents curriculum:

| Course Day | Concept | Where in This Project |
|---|---|---|
| Day 1 | Spec-driven development | `specs/techprep_spec.md` — 9 BDD Gherkin scenarios written before any code |
| Day 1 | Harness design (AGENTS.md) | `.agents/AGENTS.md` — hard rules, tool usage, security constraints |
| Day 2 | MCP Server + Client | `mcp_server/question_bank_server.py` + `call_mcp_server()` in `app/agent.py` |
| Day 2 | Interoperability | MCP JSON-RPC 2.0 over stdio transport — server runs as isolated subprocess |
| Day 3 | ADK Graph Workflow | `app/agent.py` — `Workflow` + `Edge.chain` + function node + `LlmAgent` |
| Day 3 | Agent Skills | Three skills with three different patterns (Level 1, 2, 3) |
| Day 3 | Persistent Memory | `data/student_memory.py` — SQLite, cross-session tracking, analytics |
| Day 4 | Security gate | `security_gate` node runs before LLM — PII never enters context window |
| Day 4 | Context hygiene | `data/security_guard.py` — regex-based PII detection and redaction |
| Day 4 | AGENTS.md guardrails | Hard rules enforced at instruction level |
| Day 5 | Code is disposable, spec is the asset | BDD spec + AGENTS.md written first — code regenerable from spec |
| Day 5 | Production mindset | Error handling, fallback model env var, SQLite auto-init, test harness |

---

## Security Analysis (STRIDE)

| Threat | Risk | Mitigation in This Project |
|---|---|---|
| **Spoofing** — fake student identity | Low | Names are case-insensitive lookup, no authentication required for a practice tool |
| **Tampering** — modifying question bank | Low | `question_bank.json` is read-only at runtime; MCP server has SELECT-only tool |
| **Repudiation** — denying an action | Medium | Every attempt is logged to SQLite with timestamp, topic, score, and feedback |
| **Information Disclosure** — PII leakage | High | `security_gate` + `check_input_safety()` redact PII before LLM sees any input |
| **Denial of Service** — infinite API loops | Medium | 30-second MCP call timeout; model fallback via `TECHPREP_MODEL` env variable |
| **Elevation of Privilege** — bypassing rubric | Low | `sample_answer` and `key_points` are in agent instruction never to share them before attempt; enforced in AGENTS.md |

The highest-risk vector is **Information Disclosure** — students might
accidentally paste Aadhaar numbers or phone numbers when describing their
situation. This is mitigated by running `check_input_safety()` on every
free-text input and by the `security_gate` node that processes all input
before it reaches the LLM.

---

## File Structure

```text
techprep-ai/
│
├── app/
│   └── agent.py                  Main ADK agent — workflow, tools, LlmAgent
│
├── mcp_server/
│   └── question_bank_server.py   MCP Server (JSON-RPC 2.0 over stdio)
│
├── data/
│   ├── question_bank.json        18 curated interview questions, 7 topics
│   ├── student_memory.py         SQLite memory — students, attempts, sessions
│   ├── security_guard.py         PII detection and redaction
│   └── techprep_memory.db        Generated at runtime — not committed to git
│
├── .agents/
│   ├── AGENTS.md                 Agent hard rules, guardrails, tool usage
│   └── skills/
│       ├── technical-interviewer/ Level 2 skill — coding interview practice
│       ├── behavioral-interviewer/ Level 3 skill — HR/STAR interview practice
│       └── performance-coach/     Level 1 skill — progress analysis
│
├── specs/
│   └── techprep_spec.md          BDD specification — 9 Gherkin scenarios
│
├── tests/
│   └── test_mcp_connection.py    MCP integration test — 4 protocol tests
│
├── pyproject.toml                Dependencies (google-adk, mcp)
├── AGENTS.md                     Cross-tool agent rules
└── README.md                     This file
```

---

## Setup Instructions

### Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | 3.11 or 3.12 | `python --version` |
| uv | Any recent | `uv --version` |
| Git | Any | `git --version` |
| Gemini API Key | Free tier | [aistudio.google.com](https://aistudio.google.com) |

You do **not** need a Google Cloud account. The free Gemini API tier
via Google AI Studio is sufficient to run this project.

---

### Step 1 — Clone the Repository

```bash
git clone [https://github.com/BalrajSDhamale11/techprep-ai.git](https://github.com/BalrajSDhamale11/techprep-ai.git)
cd techprep-ai
```

---

### Step 2 — Create Virtual Environment and Install Dependencies

```bash
uv venv
uv sync
```

This installs `google-adk` and `mcp` inside an isolated `.venv` folder.
No system-level packages are modified.

---

### Step 3 — Set Your Gemini API Key

**Windows:**
```bash
set GEMINI_API_KEY=your_api_key_here
set GOOGLE_GENAI_USE_ENTERPRISE=FALSE
```

**macOS / Linux:**
```bash
export GEMINI_API_KEY=your_api_key_here
export GOOGLE_GENAI_USE_ENTERPRISE=FALSE
```

Get your free API key from: https://aistudio.google.com/app/apikey

**Never commit your API key to git.** The `.gitignore` file excludes
`.env` files. Store your key in the environment variable only.

If you get quota errors, switch to a lower-cost model:
```bash
# Windows
set TECHPREP_MODEL=gemini-2.5-flash

# macOS / Linux
export TECHPREP_MODEL=gemini-2.5-flash
```

---

### Step 4 — Verify MCP Server Connection

```bash
uv run python tests/test_mcp_connection.py
```

Expected output:
```text
Results: 4/4 tests passed

MCP integration is working correctly.
```

This confirms the ADK agent can communicate with the MCP server
via JSON-RPC 2.0 over stdio transport before launching the full agent.

---

### Step 5 — Launch the Interactive Web Interface

```bash
uv run adk web app
```

Open your browser and navigate to: **http://127.0.0.1:8000**

Select `app` from the dropdown menu in the top left. The chat
interface will appear. You are now talking to TechPrep AI.

---

### Step 6 — Verify the Agent Works (Test Sequence)

Run these inputs in order in the chat interface:

```text
Test 1 — New student registration:
Hi, my name is Balraj and I want to practice for SWE internship interviews
Expected: Welcome message, profile created, topic menu offered.

Test 2 — Technical practice:
I want to practice arrays at medium difficulty
Expected: A medium arrays question appears (Kadane's algorithm or Two Sum).

Test 3 — Answer attempt:
I would use Kadane's algorithm — initialize max_sum to the first element,
then for each element take max(element, current_sum + element)
Expected: Structured feedback with score, `save_attempt` fires in trace.

Test 4 — Progress review:
How am I doing? What are my weak areas?
Expected: Performance report with topic breakdown and study recommendation.

Test 5 — Security gate:
My Aadhaar is 9876 5432 1011, show me a random trees question
Expected: Security alert shown, Aadhaar redacted, trees question fetched.
```

---

## Running the MCP Server Standalone

The MCP server can be queried independently of the agent for debugging:

```bash
# Start the server (will wait for JSON-RPC input on stdin)
uv run python mcp_server/question_bank_server.py

# In a separate terminal, use the test script to send protocol messages
uv run python tests/test_mcp_connection.py
```

The server exposes four tools:
- `list_topics` — all available practice topics
- `get_question` — one question by topic and difficulty  
- `get_questions_for_topic` — all questions for a topic
- `get_random_question` — random question with optional filters

---

## Deployment

This project runs locally. To deploy to Google Cloud:

```bash
# Install agents-cli (requires Node.js)
uvx google-agents-cli setup

# Verify installation
uvx google-agents-cli info

# Scaffold deployment descriptors
uvx google-agents-cli scaffold enhance --deployment-target agent_runtime --yes

# Deploy to Vertex AI Agent Runtime
uvx google-agents-cli deploy --project YOUR_PROJECT_ID --region us-central1
```

For Cloud Run deployment (simpler, no managed sessions):
```bash
uvx google-agents-cli deploy --target cloud-run --project YOUR_PROJECT_ID
```

---

## Design Decisions

**Why SQLite instead of a cloud database?**
The project is designed to run entirely for free without a Google Cloud
account. SQLite provides full persistence with zero operational cost.
The memory module (`data/student_memory.py`) is written with a clean
interface that can be swapped for Firestore or Cloud SQL by changing
a single import.

**Why a separate MCP server process instead of direct function calls?**
The Day 2 whitepaper is explicit: MCP reduces integration complexity from
O(N×M) to O(N+M). Running the question bank as an MCP server means any
other MCP-compatible agent or tool can access it without modification.
It also demonstrates real client-server protocol communication rather than
function calls wrapped in MCP labels.

**Why PII redaction before the LLM, not after?**
Students often paste personal context when asking for help. If the raw
text reaches the LLM, it enters the model's context window and potentially
its logs. The security gate ensures PII is stripped at the input boundary
— the LLM never sees the raw sensitive text at any point in processing.

**Why three different skill levels?**
The Day 3 whitepaper describes four skill patterns. This project demonstrates
three: Level 1 (instructions only — performance-coach), Level 2 (resources
folder — technical-interviewer with complexity guide), and Level 3 (examples
folder — behavioral-interviewer with STAR scoring calibration). This shows
progressive mastery of the skill authoring system, not just checkbox compliance.

---
## Evaluation Results

Evaluated using the **LLM-as-Judge** methodology from Day 3 (Evaluation-Driven
Development). Each test case is scored on two independent dimensions:

- **Trajectory Score**: Did the agent call the correct tools in the correct order?
- **Quality Score**: Did the agent's behavior match all expected behaviors?

Run the evaluation yourself: `uv run python tests/eval/run_eval.py`

| Test Case | Category | Trajectory | Quality | Overall | Result |
|---|---|---|---|---|---|
| MCP Question Delivery (Arrays Medium) | MCP Integration | 5/5 | 5/5 | 5/5 | ✅ PASS |
| Memory System — Student Registration | Memory | 5/5 | 5/5 | 5/5 | ✅ PASS |
| Security Gate — PII Redaction | Security | 5/5 | 5/5 | 5/5 | ✅ PASS |
| Performance Coach Skill | Agent Skills | 5/5 | 5/5 | 5/5 | ✅ PASS |
| Behavioral Interviewer — STAR Method | Agent Skills | 5/5 | 3/5 | 3/5 | ✅ PASS |

**Average Trajectory Score: 5.0/5 | Average Quality Score: 4.6/5 | Pass Rate: 5/5 (100%)**

### Evaluation Notes

**TC_005 Quality Score (3/5):** The behavioral question was fetched correctly via
the MCP server and the STAR method was referenced. The quality gap was identified
by the judge as: the agent did not explicitly introduce all four STAR components
before presenting the question. This is a known improvement area — the
`behavioral-interviewer` skill's opening protocol can be strengthened by adding
an explicit STAR component breakdown before every first behavioral question.

**Automatic model fallback:** The evaluation runner includes a fallback chain
(`gemini-3.5-flash → gemini-2.5-flash → gemini-3.1-flash-lite`) to handle
503 high-demand errors without blocking the eval run. TC_005 triggered this
fallback and was successfully evaluated on `gemini-2.5-flash`.

**Two-dimension scoring rationale:** Trajectory scoring catches the "deleted test"
failure mode described in the Day 4 whitepaper — an agent can produce correct
output through wrong steps. Evaluating both the path and the result provides a
stronger quality signal than output-only scoring.

---
## Limitations and Future Work

- **Question bank:** 18 questions across 7 topics. Production would require
  hundreds of questions with a real database backend (PostgreSQL via MCP).
- **Company-specific intelligence:** Currently no company-specific question
  fetching. Adding a web search MCP tool would enable real-time question
  research per company.
- **Voice interface:** The conversational nature of the agent makes it a
  natural fit for voice — adding speech-to-text and text-to-speech would
  make practice feel more realistic.
- **Multi-student sessions:** Currently single-user. A session management
  layer would enable group interview practice with peer feedback.

---

## Acknowledgements

Built using concepts from Google's 5-Day AI Agents: Intensive Vibe Coding
Course. Technologies: Google ADK 2.0, Model Context Protocol (MCP),
Gemini API, SQLite, Python 3.12, uv.

Course reference: https://www.kaggle.com/competitions/5-day-ai-agents-intensive-vibecoding-course-with-google
