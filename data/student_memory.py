"""
TechPrep AI — Student Memory System

Persistent storage for student profiles, practice sessions, and performance tracking.
Built on SQLite (Python built-in — no external dependencies required).

Course concept demonstrated: Long-term Memory (Day 3 — Agent Skills, Sessions & Memory)
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Database file lives in the data/ folder alongside the question bank
DB_PATH = Path(__file__).parent / "techprep_memory.db"


def get_connection() -> sqlite3.Connection:
    """
    Create and return a database connection.
    Row factory enables accessing columns by name (row['column_name']).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # enforce referential integrity
    return conn


def initialize_database() -> None:
    """
    Create all tables if they do not already exist.
    Safe to call multiple times — uses IF NOT EXISTS.
    Called once at agent startup.
    """
    conn = get_connection()
    try:
        conn.executescript("""
            -- Student profiles table
            CREATE TABLE IF NOT EXISTS students (
                student_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT    NOT NULL,
                target_role  TEXT    DEFAULT 'Software Engineer Intern',
                created_at   TEXT    NOT NULL,
                last_seen_at TEXT    NOT NULL
            );

            -- Individual question attempt records
            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id   INTEGER NOT NULL REFERENCES students(student_id),
                question_id  TEXT    NOT NULL,
                topic        TEXT    NOT NULL,
                difficulty   TEXT    NOT NULL,
                score        INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
                hints_used   INTEGER DEFAULT 0,
                feedback     TEXT,
                attempted_at TEXT    NOT NULL
            );

            -- Session-level records (one row per practice session)
            CREATE TABLE IF NOT EXISTS sessions (
                session_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id        INTEGER NOT NULL REFERENCES students(student_id),
                started_at        TEXT    NOT NULL,
                ended_at          TEXT,
                topics_covered    TEXT    DEFAULT '[]',
                questions_total   INTEGER DEFAULT 0,
                average_score     REAL    DEFAULT 0.0
            );

            -- Indexes for fast lookups
            CREATE INDEX IF NOT EXISTS idx_attempts_student
                ON attempts(student_id);

            CREATE INDEX IF NOT EXISTS idx_attempts_topic
                ON attempts(student_id, topic);

            CREATE INDEX IF NOT EXISTS idx_sessions_student
                ON sessions(student_id);
        """)
        conn.commit()
    finally:
        conn.close()


# ─── STUDENT OPERATIONS ───────────────────────────────────────────────────────

def get_or_create_student(name: str, target_role: str = "Software Engineer Intern") -> dict:
    """
    Look up a student by name (case-insensitive).
    If they don't exist, create a new profile.
    Updates last_seen_at on every call.

    Returns a dict with student information.
    """
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    try:
        # Try to find existing student
        row = conn.execute(
            "SELECT * FROM students WHERE LOWER(name) = LOWER(?)",
            (name,)
        ).fetchone()

        if row:
            # Update last seen timestamp
            conn.execute(
                "UPDATE students SET last_seen_at = ? WHERE student_id = ?",
                (now, row["student_id"])
            )
            conn.commit()
            return {
                "student_id": row["student_id"],
                "name": row["name"],
                "target_role": row["target_role"],
                "created_at": row["created_at"],
                "last_seen_at": now,
                "is_returning": True
            }
        else:
            # Create new student profile
            cursor = conn.execute(
                """
                INSERT INTO students (name, target_role, created_at, last_seen_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, target_role, now, now)
            )
            conn.commit()
            return {
                "student_id": cursor.lastrowid,
                "name": name,
                "target_role": target_role,
                "created_at": now,
                "last_seen_at": now,
                "is_returning": False
            }
    finally:
        conn.close()


def get_student_by_id(student_id: int) -> dict | None:
    """Retrieve a student profile by their ID. Returns None if not found."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM students WHERE student_id = ?",
            (student_id,)
        ).fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


# ─── ATTEMPT OPERATIONS ───────────────────────────────────────────────────────

def record_attempt(
    student_id: int,
    question_id: str,
    topic: str,
    difficulty: str,
    score: int,
    hints_used: int = 0,
    feedback: str = ""
) -> dict:
    """
    Save a completed question attempt to the database.
    Score must be between 1 and 5.
    Returns the saved attempt record.
    """
    if not 1 <= score <= 5:
        raise ValueError(f"Score must be between 1 and 5, got {score}")

    now = datetime.utcnow().isoformat()
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO attempts
                (student_id, question_id, topic, difficulty, score,
                 hints_used, feedback, attempted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (student_id, question_id, topic, difficulty, score,
             hints_used, feedback, now)
        )
        conn.commit()
        return {
            "attempt_id": cursor.lastrowid,
            "student_id": student_id,
            "question_id": question_id,
            "topic": topic,
            "difficulty": difficulty,
            "score": score,
            "hints_used": hints_used,
            "feedback": feedback,
            "attempted_at": now
        }
    finally:
        conn.close()


# ─── PERFORMANCE ANALYTICS ────────────────────────────────────────────────────

def get_topic_performance(student_id: int) -> list[dict]:
    """
    Return average score and attempt count per topic for a student.
    Sorted by average score ascending (weakest topics first).
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                topic,
                COUNT(*)        AS attempts,
                ROUND(AVG(score), 2) AS average_score,
                MAX(score)      AS best_score,
                MIN(score)      AS lowest_score
            FROM attempts
            WHERE student_id = ?
            GROUP BY topic
            ORDER BY average_score ASC
            """,
            (student_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_weak_areas(student_id: int, threshold: float = 3.0) -> list[str]:
    """
    Return a list of topics where the student's average score is below the threshold.
    Default threshold is 3.0 (below average performance).
    """
    performance = get_topic_performance(student_id)
    return [
        p["topic"] for p in performance
        if p["average_score"] < threshold
    ]


def get_strong_areas(student_id: int, threshold: float = 4.0) -> list[str]:
    """
    Return topics where the student consistently scores 4 or 5.
    Threshold of 4.0 means strong performance.
    """
    performance = get_topic_performance(student_id)
    return [
        p["topic"] for p in performance
        if p["average_score"] >= threshold
    ]


def get_full_profile(student_id: int) -> dict:
    """
    Return a complete student profile with all performance analytics.
    This is what the agent reads at the start of every session.
    """
    student = get_student_by_id(student_id)
    if not student:
        return {"error": f"No student found with ID {student_id}"}

    topic_performance = get_topic_performance(student_id)
    weak_areas = get_weak_areas(student_id)
    strong_areas = get_strong_areas(student_id)

    conn = get_connection()
    try:
        # Overall stats
        overall = conn.execute(
            """
            SELECT
                COUNT(*)             AS total_questions,
                ROUND(AVG(score), 2) AS overall_average,
                SUM(hints_used)      AS total_hints_used
            FROM attempts
            WHERE student_id = ?
            """,
            (student_id,)
        ).fetchone()

        # Recent attempts (last 10)
        recent = conn.execute(
            """
            SELECT topic, difficulty, score, attempted_at
            FROM attempts
            WHERE student_id = ?
            ORDER BY attempted_at DESC
            LIMIT 10
            """,
            (student_id,)
        ).fetchall()

        # Total session count
        session_count = conn.execute(
            "SELECT COUNT(*) AS count FROM sessions WHERE student_id = ?",
            (student_id,)
        ).fetchone()["count"]

        return {
            "student": student,
            "statistics": {
                "total_questions_attempted": overall["total_questions"] or 0,
                "overall_average_score": overall["overall_average"] or 0.0,
                "total_hints_used": overall["total_hints_used"] or 0,
                "total_sessions": session_count
            },
            "topic_performance": topic_performance,
            "weak_areas": weak_areas,
            "strong_areas": strong_areas,
            "recent_attempts": [dict(r) for r in recent]
        }
    finally:
        conn.close()


# ─── SESSION OPERATIONS ───────────────────────────────────────────────────────

def start_session(student_id: int) -> int:
    """
    Create a new session record when a student starts practicing.
    Returns the session_id.
    """
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO sessions (student_id, started_at) VALUES (?, ?)",
            (student_id, now)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def end_session(session_id: int, student_id: int) -> dict:
    """
    Close a session and compute its final statistics.
    Returns a summary of what was accomplished.
    """
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    try:
        # Find all attempts made during this session
        # (approximation: attempts after session start)
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()

        if not session:
            return {"error": f"Session {session_id} not found"}

        attempts = conn.execute(
            """
            SELECT topic, score FROM attempts
            WHERE student_id = ? AND attempted_at >= ?
            ORDER BY attempted_at
            """,
            (student_id, session["started_at"])
        ).fetchall()

        topics_covered = list({a["topic"] for a in attempts})
        total_questions = len(attempts)
        avg_score = round(
            sum(a["score"] for a in attempts) / total_questions, 2
        ) if total_questions > 0 else 0.0

        conn.execute(
            """
            UPDATE sessions
            SET ended_at = ?,
                topics_covered = ?,
                questions_total = ?,
                average_score = ?
            WHERE session_id = ?
            """,
            (now, json.dumps(topics_covered), total_questions, avg_score, session_id)
        )
        conn.commit()

        return {
            "session_id": session_id,
            "topics_covered": topics_covered,
            "questions_attempted": total_questions,
            "average_score": avg_score,
            "ended_at": now
        }
    finally:
        conn.close()


# ─── INITIALIZATION CHECK ─────────────────────────────────────────────────────

# Auto-initialize when the module is imported
initialize_database()


if __name__ == "__main__":
    # Quick smoke test — run directly to verify the module works
    print("Initializing TechPrep memory database...")
    initialize_database()
    print(f"Database created at: {DB_PATH}")

    # Create a test student
    student = get_or_create_student("Test Student", "SWE Intern")
    print(f"\nCreated student: {student}")

    # Record some test attempts
    record_attempt(student["student_id"], "arr_001", "arrays", "easy", 4, 1, "Good approach")
    record_attempt(student["student_id"], "arr_002", "arrays", "medium", 2, 3, "Missed Kadane's")
    record_attempt(student["student_id"], "beh_001", "behavioral", "general", 5, 0, "Excellent STAR")
    record_attempt(student["student_id"], "dp_001", "dynamic_programming", "medium", 1, 3, "Needs review")
    print("\nRecorded 4 test attempts")

    # Retrieve and display full profile
    profile = get_full_profile(student["student_id"])
    print(f"\nFull profile:")
    print(f"  Total questions: {profile['statistics']['total_questions_attempted']}")
    print(f"  Overall average: {profile['statistics']['overall_average_score']}")
    print(f"  Weak areas: {profile['weak_areas']}")
    print(f"  Strong areas: {profile['strong_areas']}")

    print("\nMemory system working correctly.")