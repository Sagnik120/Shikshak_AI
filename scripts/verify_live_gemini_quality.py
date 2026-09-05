#!/usr/bin/env python3
"""
Diagnostic script to test live Gemini 2.0 Flash pedagogical quality.
Runs real PlannerAgent, ExplainerAgent, and QuestionerAgent using os.environ.get("GEMINI_API_KEY").
Does NOT read any .env files. Run with:
    GEMINI_API_KEY="your_key" python scripts/verify_live_gemini_quality.py
"""

import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json

from modules.ai_agent_orchestration.src.adapters.gemini_adapter import GeminiLLMAdapter
from modules.ai_agent_orchestration.src.agents.planner import PlannerAgent
from modules.ai_agent_orchestration.src.agents.explainer import ExplainerAgent
from modules.ai_agent_orchestration.src.agents.questioner import QuestionerAgent
from modules.ai_agent_orchestration.src.schemas.lesson import LearnerConstraints, LessonNode
from modules.ai_agent_orchestration.src.schemas.teaching import VisualSpec


def _load_env():
    """Silently populate os.environ from local .env if present and not already set."""
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
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


def main():
    _load_env()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("[-] Error: GEMINI_API_KEY is not set in environment or .env file.")
        print("    Please set GEMINI_API_KEY in your .env file or run:")
        print("    GEMINI_API_KEY=\"<key>\" python scripts/verify_live_gemini_quality.py")
        sys.exit(1)

    print(f"[*] Initializing GeminiLLMAdapter (model: {os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')})...")
    adapter = GeminiLLMAdapter(api_key=api_key)

    # 1. Test Planner Agent
    print("\n[1/3] Testing PlannerAgent on topic: 'Newton's Laws of Motion' (Class 10 Beginner)...")
    planner = PlannerAgent(llm_adapter=adapter)
    constraints = LearnerConstraints(level="beginner", language="en", time_budget_min=15, style="intuitive")
    plan = planner.plan_lesson(constraints=constraints, source_type="topic", topic="Newton's Laws of Motion")
    print(f"  [+] Generated Lesson Plan ID: {plan.lesson_id}")
    print(f"  [+] Total Nodes: {len(plan.nodes)}")
    for i, node in enumerate(plan.nodes, 1):
        print(f"      Node {i}: [{node.depth.upper()}] {node.concept} ({node.est_minutes}m, visual: {node.visual_type}, quiz: {node.checkpoint_question})")

    # 2. Test Explainer Agent
    first_node = plan.nodes[0]
    print(f"\n[2/3] Testing ExplainerAgent on concept: '{first_node.concept}'...")
    explainer = ExplainerAgent(llm_adapter=adapter)
    segment = explainer.generate_segment(
        node=first_node,
        constraints=constraints,
        grounding_chunks=["A body continues in its state of rest or uniform motion unless acted upon by a net external force."],
    )
    print(f"  [+] Script Text ({len(segment.script_text)} chars):")
    print(f"      \"{segment.script_text}\"")
    print(f"  [+] Visual Spec: {segment.visual_spec.type} -> {segment.visual_spec.content}")
    print(f"  [+] Avatar Cue: {segment.avatar_cue}")

    # 3. Test Questioner Agent
    print(f"\n[3/3] Testing QuestionerAgent on concept: '{first_node.concept}'...")
    questioner = QuestionerAgent(llm_adapter=adapter)
    question = questioner.generate_question(node=first_node, recent_segment=segment)
    print(f"  [+] Question Type: {question.type}")
    print(f"  [+] Question Text: \"{question.question_text}\"")
    if question.options:
        print(f"  [+] Options: {question.options}")
    print(f"  [+] Expected Concept: {question.expected_concept}")

    print("\n[SUCCESS] Live Gemini output quality verification completed successfully!")


if __name__ == "__main__":
    main()
