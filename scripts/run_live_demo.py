#!/usr/bin/env python3
"""Shikshak AI — Live Interactive Terminal Demo.

Runs a real end-to-end teaching session through the full production pipeline:
1. Prompts for a lesson topic and learner constraints.
2. Generates a structured LessonPlan via PlannerAgent.
3. Explains the concept and synthesizes speech + visual slides via ExplainerAgent.
4. Renders a lip-synced teacher video via AvatarVoiceService (FFmpeg + Visemes).
5. Displays a checkpoint question via QuestionerAgent.
6. Interactively accepts student answer and evaluates via MLCoreService.
7. Executes AdaptationController and displays AssessmentAgent mastery report.

Usage:
    python scripts/run_live_demo.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ANSI Color formatting
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


def load_env():
    """Silently load .env if present."""
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


load_env()

from modules.backend.src.integrations.container import get_services
from modules.ai_agent_orchestration.src.schemas.lesson import LearnerConstraints
from modules.ai_agent_orchestration.src.schemas.interaction import StudentResponse
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState


def print_banner():
    print(f"\n{BLUE}{BOLD}{'=' * 75}{RESET}")
    print(f"{CYAN}{BOLD}   🎓 SHIKSHAK AI — LIVE INTERACTIVE SYSTEM DEMO{RESET}")
    print(f"   Autonomous Multi-Agent AI Teacher & Adaptive Learning Platform")
    print(f"{BLUE}{BOLD}{'=' * 75}{RESET}\n")


def main():
    print_banner()

    # 1. Initialize Production Container
    print(f"{BOLD}[1/6] Initializing AI Services & Pipeline Container...{RESET}")
    services = get_services()
    ai_service = services["ai_service"]
    avatar_service = services["avatar_voice_service"]
    ml_core_service = services["ml_core_service"]
    print(f"  {GREEN}✓{RESET} TeacherOrchestrator ready")
    print(f"  {GREEN}✓{RESET} AvatarVoiceService (FFmpeg + Visemes) ready")
    print(f"  {GREEN}✓{RESET} MLCoreService (SentenceTransformers + Evaluation) ready")

    # 2. Topic Input
    default_topic = "Newton's First Law of Motion"
    try:
        user_topic = input(f"\n{BOLD}Enter a topic to learn [{CYAN}{default_topic}{RESET}]: {RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        user_topic = ""
    topic = user_topic if user_topic else default_topic

    try:
        user_lang = input(f"{BOLD}Choose teaching language (en / hi / hinglish) [{CYAN}en{RESET}]: {RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        user_lang = ""
    language = user_lang.lower() if user_lang in ("en", "hi", "hinglish") else "en"

    # 3. Create Session & Plan
    session_id = f"demo_{int(time.time())}"
    session = ai_service.init_session(session_id)
    constraints = LearnerConstraints(level="beginner", language=language, time_budget_min=10, style="intuitive")

    print(f"\n{BOLD}[2/6] Generating Pedagogical Lesson Plan for: '{topic}'...{RESET}")
    current_state, _ = ai_service.process_next_step(session_id, TeacherState.UNDERSTAND, {"topic": topic, "constraints": constraints})
    current_state, plan = ai_service.process_next_step(session_id, current_state, {})
    print(f"  {GREEN}✓{RESET} Plan ID: {plan.lesson_id}")
    print(f"  {GREEN}✓{RESET} Curriculum Nodes:")
    for i, node in enumerate(plan.nodes, 1):
        print(f"     {BOLD}{i}. [{node.depth.upper()}]{RESET} {node.concept} ({node.est_minutes} mins, Visual: {node.visual_type})")

    # 4. Teach Node 1 (Explain & Render Video)
    first_node = plan.nodes[0]
    first_node.checkpoint_question = True
    print(f"\n{BOLD}[3/6] Teaching Node 1: '{first_node.concept}'...{RESET}")
    current_state, segment = ai_service.process_next_step(session_id, current_state, {})
    
    print(f"\n  {MAGENTA}{BOLD}Teacher Script:{RESET}")
    print(f"  \"{segment.script_text}\"")
    print(f"  Visual Spec: [{segment.visual_spec.type.upper()}] {segment.visual_spec.content}")

    # Render video
    print(f"\n{BOLD}[4/6] Rendering Synchronized Lip-Synced Video (FFmpeg + 24 FPS Visemes)...{RESET}")
    current_state, payload = ai_service.process_next_step(session_id, current_state, {"segment": segment})
    job_id = payload.get("job_id") if isinstance(payload, dict) else None

    if job_id:
        while True:
            status = avatar_service.get_status(job_id)
            if status and status.status == "done":
                rendered = status.result
                print(f"  {GREEN}✓{RESET} Video successfully rendered in {rendered.duration_sec}s audio duration!")
                print(f"  {GREEN}✓{RESET} MP4 Video Path: {CYAN}{rendered.video_url}{RESET}")
                if rendered.captions_vtt_url:
                    print(f"  {GREEN}✓{RESET} WebVTT Subtitles: {rendered.captions_vtt_url}")
                print(f"\n  {YELLOW}👉 Tip: Open and watch this video in macOS QuickTime with:{RESET}")
                print(f"     {CYAN}open \"{rendered.video_url}\"{RESET}")
                break
            elif status and status.status == "failed":
                print(f"  {RED}✗{RESET} Video rendering failed: {status.error}")
                break
            time.sleep(0.5)

    # 5. Checkpoint Question
    print(f"\n{BOLD}[5/6] Generating Pedagogical Checkpoint Question...{RESET}")
    if current_state == TeacherState.QUESTION:
        current_state, question = ai_service.process_next_step(session_id, current_state, {})
    else:
        question = ai_service.orchestrator.questioner.generate_question(first_node, segment)
        current_state = TeacherState.EVALUATE


    print(f"\n{BLUE}{BOLD}{'-' * 70}{RESET}")
    print(f"{CYAN}{BOLD}❓ Checkpoint Question:{RESET} {question.question_text}")
    
    option_letters = ["A", "B", "C", "D", "E"]
    correct_letter = "A"
    if question.options:
        for idx, opt in enumerate(question.options):
            letter = option_letters[idx] if idx < len(option_letters) else str(idx + 1)
            print(f"   [{BOLD}{letter}{RESET}] {opt}")
            if opt.strip().lower() == question.expected_concept.strip().lower():
                correct_letter = letter

    print(f"{BLUE}{BOLD}{'-' * 70}{RESET}")

    # Prompt user for answer
    try:
        user_answer = input(f"\n{BOLD}Enter your answer (or press Enter for correct answer): {RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        user_answer = ""

    # Map letter to option text if user typed A/B/C/D
    actual_answer = user_answer
    if user_answer.upper() in option_letters and question.options:
        opt_idx = option_letters.index(user_answer.upper())
        if opt_idx < len(question.options):
            actual_answer = question.options[opt_idx]
    elif not actual_answer:
        # Default to expected concept
        actual_answer = question.expected_concept
        print(f"  (Auto-answering with correct answer: '{actual_answer}')")

    student_response = StudentResponse(
        node_id=first_node.node_id,
        raw_answer=actual_answer,
        response_type=question.type,
        response_time_sec=3.5,
    )

    # 6. Evaluate & Adapt
    print(f"\n{BOLD}[6/6] Evaluating Response & Computing Pedagogical Adaptation...{RESET}")
    current_state, eval_result = ai_service.process_next_step(session_id, current_state, {"student_response": student_response})
    
    print(f"  • Correct:     {'✅ Yes' if eval_result.correct else '❌ No'}")
    print(f"  • Confidence:  {eval_result.confidence * 100:.1f}%")
    print(f"  • Feedback:    {eval_result.feedback_text}")

    current_state, decision = ai_service.process_next_step(session_id, current_state, {"eval_result": eval_result})
    print(f"  • Decision:    {BOLD}{decision.action}{RESET} ({decision.reason})")

    # Generate the final Assessment Report
    assessor = ai_service.orchestrator.assessor
    report = assessor.generate_report(session.lesson_plan.lesson_id, [eval_result])

    print(f"\n{BLUE}{BOLD}{'=' * 75}{RESET}")
    print(f"{GREEN}{BOLD}   🎉 SESSION MASTERY REPORT (AssessmentAgent){RESET}")
    print(f"{BLUE}{BOLD}{'=' * 75}{RESET}")
    print(f"  • Mastery Score:      {BOLD}{report.score_pct:.1f}%{RESET}")
    print(f"  • Strong Areas:       {', '.join(report.strong_areas) if report.strong_areas else 'None'}")
    print(f"  • Weak Areas:         {', '.join(report.weak_areas) if report.weak_areas else 'None'}")
    print(f"  • Recommended Next:   {', '.join(report.recommended_next) if report.recommended_next else 'Advanced Practice'}")
    print(f"  • Teacher Narrative:  \"{report.narrative_feedback}\"")
    print(f"{BLUE}{BOLD}{'=' * 75}{RESET}\n")


if __name__ == "__main__":
    main()
